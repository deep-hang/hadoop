#!/usr/bin/env bash
#
# 边界输入用例：大小写、标点、空行、中文与数字。
#
# 前置条件：2—4 号模块已就绪（HDFS 可写、YARN 可提交作业），且已执行 build.sh。
# 执行位置：项目根目录。
#   bash tests/wordcount/check-edge-cases.sh
#
# 固定输入：tests/wordcount/cases/edge/*.txt（4 个文件）
# 预期：tests/wordcount/cases/expected/edge.tsv
#   hello=3、hadoop=6、数据=3、分析=1、2026=2
#   其中 blank.txt 只有空行、空格、制表符和标点，预期不产生任何单词。
# 输出目录：/project/output/wordcount/edge-001（已存在时脚本直接失败，不删除旧结果）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
APP_DIR="${PROJECT_ROOT}/apps/wordcount"

# shellcheck disable=SC1091
. "${PROJECT_ROOT}/.development"

HADOOP_BIN="${HADOOP_HOME:-/opt/hadoop}/bin/hadoop"
INPUT_DIR_HDFS="${HDFS_INPUT_ROOT:-/project/input}/wordcount-edge"
OUTPUT_DIR_HDFS="${HDFS_OUTPUT_ROOT:-/project/output}/wordcount/edge-001"
EXPECTED="${SCRIPT_DIR}/cases/expected/edge.tsv"

if ! "${HADOOP_BIN}" fs -ls / >/dev/null 2>&1; then
    echo "SKIP: HDFS 不可用，本用例需要 3 号模块的 HDFS 与 4 号模块的 YARN 就绪。" >&2
    exit 1
fi
[ -f "${EXPECTED}" ] || { echo "FAIL: 缺少预期文件 ${EXPECTED}" >&2; exit 1; }

echo "== 1. 上传边界输入 =="
"${HADOOP_BIN}" dfs -mkdir -p "${INPUT_DIR_HDFS}"
"${HADOOP_BIN}" dfs -put -f "${SCRIPT_DIR}"/cases/edge/*.txt "${INPUT_DIR_HDFS}"
"${HADOOP_BIN}" dfs -ls "${INPUT_DIR_HDFS}"

echo "== 2. 运行作业 =="
bash "${APP_DIR}/run.sh" "${INPUT_DIR_HDFS}" "${OUTPUT_DIR_HDFS}"

echo "== 3. 核对该数据集的实际输出 =="
WORDCOUNT_EXPECTED="${EXPECTED}" bash "${APP_DIR}/verify.sh" "${OUTPUT_DIR_HDFS}"

echo "EDGE CASES PASS"
