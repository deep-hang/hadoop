#!/usr/bin/env bash
#
# 核对 WordCount 的输出结果。
#
# 接口（见 docs/interfaces.md）：
#   bash apps/wordcount/verify.sh <输出路径>     正确 0，错误非 0
#
# 做什么：
#   1. 确认输出位置存在，并至少有一个 part-r-* 结果文件（不把 _SUCCESS 当作唯一证据）；
#   2. 把全部 part-r-* 读出来，按“单词 -> 次数”累加（多 Reduce 任务时同一单词不会跨文件重复，
#      但累加写法能兼容被拆分过的输出）；
#   3. 与预期词频逐行比对：单词集合、每个单词的次数都必须完全一致，多一个词或少一个词都算失败。
#
# 预期从哪来：
#   默认核对本模块 README 固定的最小样例（input/a.txt + input/b.txt）：
#       hadoop=2  hello=2  world=1
#   核对其他数据集时用环境变量指定预期文件，两列：单词 制表符 次数（空格分隔也接受），
#       WORDCOUNT_EXPECTED=tests/wordcount/cases/expected/large.tsv \
#         bash apps/wordcount/verify.sh /project/output/wordcount/large-001
#
# 路径语义与 run.sh 一致：不带协议头的按 HDFS 路径解释（自动补 HDFS_URI）；
# WORDCOUNT_LOCAL=1 时按本地路径解释。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [ -f "${PROJECT_ROOT}/.development" ]; then
    # shellcheck disable=SC1091
    . "${PROJECT_ROOT}/.development"
fi

HADOOP_HOME="${HADOOP_HOME:-/opt/hadoop}"
HADOOP_BIN="${HADOOP_HOME}/bin/hadoop"
HDFS_URI="${HDFS_URI:-hdfs://master:9000}"
LOCAL_MODE="${WORDCOUNT_LOCAL:-0}"
EXPECTED_FILE="${WORDCOUNT_EXPECTED:-}"

usage() {
    cat >&2 <<'EOF'
用法: bash verify.sh <输出路径>

  默认按固定小样例核对（hadoop=2 hello=2 world=1）:
    bash verify.sh /project/output/wordcount/run-001

  核对其他数据集:
    WORDCOUNT_EXPECTED=tests/wordcount/cases/expected/large.tsv \
      bash verify.sh /project/output/wordcount/large-001

  本地调试模式的输出:
    WORDCOUNT_LOCAL=1 bash verify.sh /tmp/wordcount-out
EOF
}

if [ "$#" -ne 1 ]; then
    usage
    exit 2
fi

OUTPUT="$1"
[ -n "${OUTPUT}" ] || { echo "VERIFY FAIL: 输出路径为空" >&2; exit 2; }

TMP_DIR="$(mktemp -d)"
cleanup() {
    rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

fail() {
    echo "VERIFY FAIL: $*" >&2
    exit 1
}

to_uri() {
    case "$1" in
        *://*) printf '%s' "$1" ;;
        *)     printf '%s%s' "${2%/}" "$1" ;;
    esac
}

# ---------- 第 1 步：取出 part-r-* 的原始内容 ----------
# 判定位置类型：带协议头按协议；否则看本地模式开关。
case "${OUTPUT}" in
    file://*)  LOCAL_PATH="${OUTPUT#file://}"; MODE="local" ;;
    *://*)     MODE="hdfs" ;;
    *)         if [ "${LOCAL_MODE}" = "1" ]; then MODE="local"; LOCAL_PATH="${OUTPUT}"; else MODE="hdfs"; fi ;;
esac

RAW_FILE="${TMP_DIR}/raw.tsv"

if [ "${MODE}" = "local" ]; then
    if [ -f "${LOCAL_PATH}" ]; then
        # 允许直接指向一个结果文件。
        cat "${LOCAL_PATH}" > "${RAW_FILE}"
        RESULT_FILES="1"
    else
        [ -d "${LOCAL_PATH}" ] || fail "本地输出目录不存在: ${LOCAL_PATH}"
        shopt -s nullglob
        PART_FILES=("${LOCAL_PATH}"/part-r-*)
        shopt -u nullglob
        [ "${#PART_FILES[@]}" -gt 0 ] || fail "输出目录里没有 part-r-* 结果文件: ${LOCAL_PATH}"
        cat "${PART_FILES[@]}" > "${RAW_FILE}"
        RESULT_FILES="${#PART_FILES[@]}"
        if ls "${LOCAL_PATH}"/part-m-* >/dev/null 2>&1; then
            echo "WARN: 存在 part-m-*，说明作业没有 Reduce 阶段，结果不是最终词频。" >&2
        fi
    fi
else
    [ -x "${HADOOP_BIN}" ] || fail "找不到 hadoop 命令 ${HADOOP_BIN}"
    OUT_URI="$(to_uri "${OUTPUT}" "${HDFS_URI}")"
    "${HADOOP_BIN}" fs -test -d "${OUT_URI}" 2>/dev/null || fail "HDFS 输出目录不存在: ${OUT_URI}"
    RESULT_FILES="$("${HADOOP_BIN}" fs -ls "${OUT_URI}" 2>/dev/null | grep -c '/part-r-' || true)"
    [ "${RESULT_FILES}" -gt 0 ] || fail "HDFS 输出目录里没有 part-r-* 结果文件: ${OUT_URI}"
    # 让 HDFS 自己展开通配符，避免依赖本地文件系统里恰好有同名文件。
    "${HADOOP_BIN}" fs -cat "${OUT_URI}/part-r-*" > "${RAW_FILE}" \
        || fail "读取 part-r-* 失败: ${OUT_URI}/part-r-*"
    echo "输出位置: ${OUT_URI}"
    if ! "${HADOOP_BIN}" fs -test -e "${OUT_URI}/_SUCCESS" 2>/dev/null; then
        echo "WARN: 缺少 _SUCCESS 标记，作业可能没有正常结束（继续核对内容）。" >&2
    fi
fi

# ---------- 第 2 步：按单词累加 ----------
# 默认输出用制表符分隔：单词 \t 次数；这里也容忍空格分隔。
# 顺带剥掉行首可能存在的 UTF-8 BOM（Windows 编辑器保存的 TSV 常带），否则第一个单词会对不上。
if ! awk -F'[\t ]+' '{ sub(/^\357\273\277/, "", $1) } NF>=2 && $1!="" {count[$1]+=$2; lines++} END {
        if (lines == 0) { exit 3 }
        for (word in count) { printf "%s\t%d\n", word, count[word] }
    }' "${RAW_FILE}" > "${TMP_DIR}/actual.unsorted"; then
    fail "结果文件里没有可解析的“单词 次数”行（文件为空或格式异常）"
fi

LC_ALL=C sort -k1,1 "${TMP_DIR}/actual.unsorted" > "${TMP_DIR}/actual.tsv"

# ---------- 第 3 步：准备预期 ----------
EXPECTED_SOURCE_DESC="固定小样例（input/a.txt + input/b.txt）"
if [ -n "${EXPECTED_FILE}" ]; then
    [ -f "${EXPECTED_FILE}" ] || fail "预期文件不存在: ${EXPECTED_FILE}"
    EXPECTED_SRC="${EXPECTED_FILE}"
    EXPECTED_SOURCE_DESC="${EXPECTED_FILE}"
else
    EXPECTED_SRC="${TMP_DIR}/expected.default"
    printf 'hadoop\t2\nhello\t2\nworld\t1\n' > "${EXPECTED_SRC}"
fi

awk -F'[\t ]+' '{ sub(/^\357\273\277/, "", $1) } NF>=2 && $1!="" {print $1"\t"$2}' "${EXPECTED_SRC}" \
    | LC_ALL=C sort -k1,1 > "${TMP_DIR}/expected.tsv"

[ -s "${TMP_DIR}/expected.tsv" ] || fail "预期词频为空: ${EXPECTED_SOURCE_DESC}"

# ---------- 第 4 步：逐词比对 ----------
ACTUAL_WORDS="$(wc -l < "${TMP_DIR}/actual.tsv" | tr -d ' ')"
EXPECTED_WORDS="$(wc -l < "${TMP_DIR}/expected.tsv" | tr -d ' ')"

if ! diff -u "${TMP_DIR}/expected.tsv" "${TMP_DIR}/actual.tsv" > "${TMP_DIR}/diff.txt"; then
    echo "VERIFY FAIL: 词频与预期不一致" >&2
    echo "  预期来源: ${EXPECTED_SOURCE_DESC}" >&2
    echo "  预期 ${EXPECTED_WORDS} 个单词，实际 ${ACTUAL_WORDS} 个单词" >&2
    echo "  差异（- 预期 / + 实际）:" >&2
    sed -e '1,2d' -e 's/^/    /' "${TMP_DIR}/diff.txt" >&2
    exit 1
fi

echo "VERIFY PASS: ${ACTUAL_WORDS} 个单词与预期完全一致（结果文件 ${RESULT_FILES} 个）"
echo "  预期来源: ${EXPECTED_SOURCE_DESC}"
awk -F'\t' '{printf "    %-20s %s\n", $1, $2}' "${TMP_DIR}/actual.tsv"
