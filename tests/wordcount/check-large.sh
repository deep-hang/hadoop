#!/usr/bin/env bash
#
# 较大规模、多文件输入的用例，用于演示两个 Worker 都参与计算。
#
# 前置条件：HDFS、YARN 已就绪，且已执行 build.sh。
# 执行位置：项目根目录。
#   bash tests/wordcount/check-large.sh [文件数] [每个文件行数]
#
# 流程：
#   1. gen-large-input.sh 生成多文件输入，并用 shell 工具独立算出预期词频；
#   2. 把输入上传到 /project/input/wordcount-large；
#   3. 提交作业到 /project/output/wordcount/large-001；
#   4. 用该数据集的预期核对输出；
#   5. 打印 YARN 上这个作业的 Map/Reduce 任务数和容器所在节点，作为“分布式执行”的证据。
#
# 输出目录已存在时直接失败，不删除旧结果；重复演示请先自行确认旧结果是否还需要。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
APP_DIR="${PROJECT_ROOT}/apps/wordcount"

# shellcheck disable=SC1091
. "${PROJECT_ROOT}/.development"

HADOOP_BIN="${HADOOP_HOME:-/opt/hadoop}/bin/hadoop"
HDFS_BIN="${HADOOP_HOME:-/opt/hadoop}/bin/hdfs"
INPUT_DIR_HDFS="${HDFS_INPUT_ROOT:-/project/input}/wordcount-large"
OUTPUT_DIR_HDFS="${HDFS_OUTPUT_ROOT:-/project/output}/wordcount/large-001"

FILE_COUNT="${1:-5}"
LINES_PER_FILE="${2:-2000}"

if ! "${HADOOP_BIN}" fs -ls / >/dev/null 2>&1; then
    echo "SKIP: HDFS 不可用，本用例需要 3 号模块的 HDFS 与 4 号模块的 YARN 就绪。" >&2
    exit 1
fi

echo "== 1. 生成输入与预期 =="
bash "${SCRIPT_DIR}/gen-large-input.sh" "${FILE_COUNT}" "${LINES_PER_FILE}"
LOCAL_INPUT="${SCRIPT_DIR}/build/large"
EXPECTED="${SCRIPT_DIR}/build/expected/large.tsv"

echo "== 2. 上传到 HDFS =="
"${HDFS_BIN}" dfs -mkdir -p "${INPUT_DIR_HDFS}"
"${HDFS_BIN}" dfs -put -f "${LOCAL_INPUT}"/*.txt "${INPUT_DIR_HDFS}"
"${HDFS_BIN}" dfs -du -h "${INPUT_DIR_HDFS}"

echo "== 3. 提交作业（Reduce 任务数默认 2，让两个 Worker 都有 Reduce 任务）=="
bash "${APP_DIR}/run.sh" "${INPUT_DIR_HDFS}" "${OUTPUT_DIR_HDFS}"

echo "== 4. 核对输出 =="
WORDCOUNT_EXPECTED="${EXPECTED}" bash "${APP_DIR}/verify.sh" "${OUTPUT_DIR_HDFS}"

echo "== 5. 分布式执行证据 =="
echo "结果文件个数（等于完成的 Reduce 任务数）:"
"${HDFS_BIN}" dfs -ls "${OUTPUT_DIR_HDFS}" | grep -c 'part-r-' || true
echo
echo "该作业的容器分布（同一个 Application 的 Map/Reduce 任务跑在哪些节点）："
"${HADOOP_BIN}" job -list 2>/dev/null | tail -n +2 | head -3 || true
cat <<'EOF'
  提交作业时控制台会打印 tracking URL，用浏览器打开 YARN UI（8088）也能看到：
    - 该 application 的 Map 任务数 = 输入分片数（5 个文件 => 通常 5 个 Map 任务）
    - Reduce 任务数 = 2
    - 每个任务 Attempt 所在节点，应同时出现 worker1 与 worker2
  截图时请保留 application id、任务数和节点名，只截“节点在线”不算证据。
EOF

echo "LARGE INPUT PASS"
