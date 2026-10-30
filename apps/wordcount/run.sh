#!/usr/bin/env bash
#
# 运行 WordCount 作业。
#
# 接口（见 docs/interfaces.md）：
#   bash apps/wordcount/run.sh <输入路径> <输出路径>     成功 0，失败非 0
#
# 路径语义：
#   正式联调时输入、输出都按 HDFS 路径解释，例如
#       bash apps/wordcount/run.sh /project/input/wordcount /project/output/wordcount/run-001
#   不带协议头的路径会自动补上 .development 里的 HDFS_URI（默认 hdfs://master:9000）。
#
# 可选环境变量：
#   WORDCOUNT_REDUCERS  Reduce 任务数，默认 2。设成 2 是为了让两个 Worker 都能领到
#                       Reduce 任务，便于演示“计算分布”；小输入下任务量很小，结果不受影响。
#   WORDCOUNT_LOCAL=1   本地模式调试：不连 HDFS/YARN，改用 file:// 和 LocalJobRunner。
#                       只用于上游集群未就绪时验证逻辑，不能当作 YARN 上的验收结果。
#
# 前置条件：
#   - 已执行 build.sh，存在 build/wordcount.jar
#   - 正式模式：HDFS、YARN 已由 3、4 号模块启动，当前用户在 HDFS 有写权限
#   - 输出目录必须不存在；已存在时直接失败，不递归删除用户数据
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
JAR_FILE="${SCRIPT_DIR}/build/wordcount.jar"
MAIN_CLASS="com.hadooplab.wordcount.WordCountDriver"
REDUCERS="${WORDCOUNT_REDUCERS:-2}"
LOCAL_MODE="${WORDCOUNT_LOCAL:-0}"

usage() {
    cat >&2 <<'EOF'
用法: bash run.sh <输入路径> <输出路径>

  HDFS 模式（正式）:
    bash run.sh /project/input/wordcount /project/output/wordcount/run-001

  本地调试模式（不连集群，不能作为验收结果）:
    WORDCOUNT_LOCAL=1 bash run.sh /workspace/apps/wordcount/input /tmp/wordcount-out

  可选: WORDCOUNT_REDUCERS=2（默认 2，指定 Reduce 任务数）
EOF
}

if [ "$#" -ne 2 ]; then
    usage
    exit 2
fi

INPUT="$1"
OUTPUT="$2"

[ -n "${INPUT}" ] || { echo "RUN FAIL: 输入路径为空" >&2; exit 2; }
[ -n "${OUTPUT}" ] || { echo "RUN FAIL: 输出路径为空" >&2; exit 2; }
[ -f "${JAR_FILE}" ] || { echo "RUN FAIL: 找不到 ${JAR_FILE}，请先执行 bash build.sh" >&2; exit 2; }
[ -x "${HADOOP_BIN}" ] || { echo "RUN FAIL: 找不到 hadoop 命令 ${HADOOP_BIN}" >&2; exit 2; }

# 把路径补成完整 URI：已带协议头（file://、hdfs://）的原样使用。
to_uri() {
    case "$1" in
        *://*) printf '%s' "$1" ;;
        *)     printf '%s%s' "${2%/}" "$1" ;;
    esac
}

if [ "${LOCAL_MODE}" = "1" ]; then
    # ---------- 本地调试：file:// + LocalJobRunner ----------
    case "${INPUT}" in
        /*) : ;;
        *) echo "RUN FAIL: 本地模式要求输入为绝对路径，收到 ${INPUT}" >&2; exit 2 ;;
    esac
    case "${OUTPUT}" in
        /*) : ;;
        *) echo "RUN FAIL: 本地模式要求输出为绝对路径，收到 ${OUTPUT}" >&2; exit 2 ;;
    esac

    INPUT_URI="$(to_uri "${INPUT}" "file://")"
    OUTPUT_URI="$(to_uri "${OUTPUT}" "file://")"

    [ -e "${INPUT}" ] || { echo "RUN FAIL: 本地输入不存在 ${INPUT}" >&2; exit 2; }
    if [ -e "${OUTPUT}" ]; then
        echo "RUN FAIL: 本地输出已存在，拒绝覆盖 ${OUTPUT}" >&2
        exit 2
    fi

    echo "[本地调试模式] 不提交到 YARN，结果仅用于逻辑验证。"
    EXTRA_OPTS=(-D mapreduce.framework.name=local -D fs.defaultFS=file:///)
else
    # ---------- HDFS 模式：提交到 YARN ----------
    INPUT_URI="$(to_uri "${INPUT}" "${HDFS_URI}")"
    OUTPUT_URI="$(to_uri "${OUTPUT}" "${HDFS_URI}")"

    if ! "${HADOOP_BIN}" fs -test -e "${INPUT_URI}" 2>/dev/null; then
        echo "RUN FAIL: HDFS 输入不存在 ${INPUT_URI}" >&2
        echo "  先上传固定输入: hdfs dfs -mkdir -p ${HDFS_INPUT_ROOT:-/project/input}/wordcount" >&2
        echo "                  hdfs dfs -put ${SCRIPT_DIR}/input/*.txt ${HDFS_INPUT_ROOT:-/project/input}/wordcount" >&2
        exit 2
    fi
    if "${HADOOP_BIN}" fs -test -e "${OUTPUT_URI}" 2>/dev/null; then
        echo "RUN FAIL: HDFS 输出已存在，拒绝覆盖 ${OUTPUT_URI}" >&2
        echo "  重复演示请换新的子目录，例如 run-002；确认要丢弃旧结果时由使用者自己删除。" >&2
        exit 2
    fi
    EXTRA_OPTS=()
fi

echo "输入 : ${INPUT_URI}"
echo "输出 : ${OUTPUT_URI}"
echo "Reducer 数 : ${REDUCERS}"

# -D 参数必须放在两个路径参数之前，由 ToolRunner 解析进 Configuration。
set +e
"${HADOOP_BIN}" jar "${JAR_FILE}" "${MAIN_CLASS}" \
    -D mapreduce.job.reduces="${REDUCERS}" \
    ${EXTRA_OPTS[@]+"${EXTRA_OPTS[@]}"} \
    "${INPUT_URI}" "${OUTPUT_URI}"
EXIT_CODE=$?
set -e

if [ "${EXIT_CODE}" -ne 0 ]; then
    echo "RUN FAIL: 作业返回 ${EXIT_CODE}" >&2
    exit "${EXIT_CODE}"
fi

echo "RUN PASS: ${OUTPUT_URI}"
