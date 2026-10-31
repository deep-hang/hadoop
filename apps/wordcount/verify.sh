#!/usr/bin/env bash
#
# 核对 WordCount 的输出结果。
#
# 接口（见 docs/interfaces.md）：
#   bash apps/wordcount/verify.sh <输出路径>     正确 0，错误非 0
#
# 做什么：
#   1. 确认输出位置存在，并至少有一个 part-r-* 结果文件（不把 _SUCCESS 当作唯一证据）；
#   2. 逐行校验格式：每行必须恰好两列（单词 + 次数），次数必须是非负十进制整数。
#      格式不对的行不会被“跳过”或“四舍五入”，而是直接判定失败并打印出问题的那几行
#      （例如只写了一列的残行、次数写成 2.9、负数、三列等）；
#   3. 把全部 part-r-* 读出来，按“单词 -> 次数”累加（多 Reduce 任务时同一单词不会跨文件重复，
#      但累加写法能兼容被拆分过的输出）；
#   4. 与预期词频逐行比对：单词集合、每个单词的次数都必须完全一致，多一个词或少一个词都算失败。
#      预期文件同样做格式校验，写错的预期不会被当成“合法的参考答案”。
#
# 预期从哪来：
#   默认核对本模块 README 固定的最小样例（input/a.txt + input/b.txt）：
#       hadoop=2  hello=2  world=1
#   核对其他数据集时用环境变量指定预期文件，两列：单词 制表符 次数（空格分隔也接受），
#   预期文件本身也按同一格式校验，写错一行会直接报错而不是拿去比对：
#       WORDCOUNT_EXPECTED=tests/wordcount/build/expected/large.tsv \
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
    WORDCOUNT_EXPECTED=tests/wordcount/build/expected/large.tsv \
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
    rm -rf "${TMP_DIR}" 2>/dev/null || true
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

# ---------- 第 2 步：逐行校验格式，并按单词累加 ----------
# 默认输出用制表符分隔：单词 \t 次数；这里也容忍空格分隔。
# 每行都必须严格解析，不能“看不懂就跳过”：
#   - 结果是两列，多一列少一列都算错（残行、拼接错位都在这里被拦住）；
#   - 次数必须匹配 ^[0-9]+$，用字符串判断而不是数值判断，否则 awk 会把 2.9 静默截断成 2；
#   - 负数、小数、空次数、非数字全部算错。
# 行首 UTF-8 BOM 和行尾 CR 只是编码差异，先剥掉再判断；完全空白的行不携带数据，跳过。
FORMAT_ERRORS="${TMP_DIR}/result-format-errors.txt"
# 错误清单路径通过环境变量交给 awk：awk 的 -v 赋值会解释反斜杠，
# Windows 下临时目录形如 C:\Users\... 会被吃成 C:Users...，改用 ENVIRON 原样传递。
AWK_RC=0
WC_FORMAT_ERRORS="${FORMAT_ERRORS}" awk '
    BEGIN { errfile = ENVIRON["WC_FORMAT_ERRORS"] }
    function bad(msg) {
        nbad++
        if (nbad <= 10) printf("  第 %d 行 %s: [%s]\n", NR, msg, line) > errfile
    }
    {
        line = $0
        sub(/\r$/, "", line)
        sub(/^\357\273\277/, "", line)
        if (line ~ /^[ \t]*$/) next
        nf = split(line, fields, /[ \t]+/)
        if (nf != 2)             { bad("应为两列（单词 + 次数），实际 " nf " 列"); next }
        if (fields[1] == "")     { bad("单词为空"); next }
        if (fields[2] !~ /^[0-9]+$/) { bad("次数不是非负整数"); next }
        count[fields[1]] += fields[2] + 0
        rows++
    }
    END {
        if (nbad > 0) {
            printf("  ……共 %d 行格式错误\n", nbad) > errfile
            exit 4
        }
        if (rows == 0) exit 3
        for (word in count) { printf "%s\t%d\n", word, count[word] }
    }
' "${RAW_FILE}" > "${TMP_DIR}/actual.unsorted" || AWK_RC=$?

case "${AWK_RC}" in
    0) ;;
    3)
        fail "结果文件里没有可解析的“单词 次数”行（文件为空）"
        ;;
    *)
        echo "VERIFY FAIL: 结果格式错误，每行必须是“单词 次数”，且次数为非负整数" >&2
        echo "  问题行（最多列出前 10 行）:" >&2
        if [ -s "${FORMAT_ERRORS}" ]; then cat "${FORMAT_ERRORS}" >&2; fi
        exit 1
        ;;
esac

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

# 预期文件走同一套格式规则：写错一行就报错，而不是拿一份坏答案去比。
EXPECTED_ERRORS="${TMP_DIR}/expected-format-errors.txt"
EXPECTED_RC=0
WC_EXPECTED_ERRORS="${EXPECTED_ERRORS}" awk '
    BEGIN { errfile = ENVIRON["WC_EXPECTED_ERRORS"] }
    function bad(msg) {
        nbad++
        if (nbad <= 10) printf("  第 %d 行 %s: [%s]\n", NR, msg, line) > errfile
    }
    {
        line = $0
        sub(/\r$/, "", line)
        sub(/^\357\273\277/, "", line)
        if (line ~ /^[ \t]*$/) next
        nf = split(line, fields, /[ \t]+/)
        if (nf != 2)             { bad("应为两列（单词 + 次数），实际 " nf " 列"); next }
        if (fields[1] == "")     { bad("单词为空"); next }
        if (fields[2] !~ /^[0-9]+$/) { bad("次数不是非负整数"); next }
        print fields[1]"\t"fields[2]
    }
    END { if (nbad > 0) exit 4 }
' "${EXPECTED_SRC}" | LC_ALL=C sort -k1,1 > "${TMP_DIR}/expected.tsv" || EXPECTED_RC=$?

if [ "${EXPECTED_RC}" -ne 0 ]; then
    echo "VERIFY FAIL: 预期文件格式错误，每行必须是“单词 次数”，且次数为非负整数" >&2
    echo "  预期来源: ${EXPECTED_SOURCE_DESC}" >&2
    if [ -s "${EXPECTED_ERRORS}" ]; then cat "${EXPECTED_ERRORS}" >&2; fi
    exit 1
fi

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
