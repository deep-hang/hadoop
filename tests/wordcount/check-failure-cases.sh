#!/usr/bin/env bash
#
# 失败用例：确认“出错时明确失败”，而不是默默返回成功。
#
# 前置条件：HDFS、YARN 已就绪（3、4 号模块），且已执行 build.sh。
# 执行位置：项目根目录。
#   bash tests/wordcount/check-failure-cases.sh
#
# 覆盖四项：
#   1. 输入不存在          -> run.sh 必须非 0
#   2. 输出已存在          -> run.sh 必须非 0，且不删除已有数据
#   3. 核对不存在的输出     -> verify.sh 必须非 0
#   4. 用错误的预期去核对   -> verify.sh 必须非 0
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
APP_DIR="${PROJECT_ROOT}/apps/wordcount"

# shellcheck disable=SC1091
. "${PROJECT_ROOT}/.development"

HADOOP_BIN="${HADOOP_HOME:-/opt/hadoop}/bin/hadoop"
HDFS_BIN="${HADOOP_HOME:-/opt/hadoop}/bin/hdfs"
INPUT_DIR_HDFS="${HDFS_INPUT_ROOT:-/project/input}/wordcount"
OUTPUT_ROOT="${HDFS_OUTPUT_ROOT:-/project/output}/wordcount"
GUARD_DIR="${OUTPUT_ROOT}/failure-case-guard"

mkdir -p "${SCRIPT_DIR}/build"

PASS=0
FAIL=0
ok() { PASS=$((PASS + 1)); echo "  PASS  $1"; }
ng() { FAIL=$((FAIL + 1)); echo "  FAIL  $1"; }

expect_nonzero() {
    local desc="$1"
    shift
    "$@" >/dev/null 2>&1
    local code=$?
    if [ "${code}" -ne 0 ]; then ok "${desc}（退出码 ${code}）"; else ng "${desc}（期望非 0，实际 0）"; fi
}

if ! "${HADOOP_BIN}" fs -ls / >/dev/null 2>&1; then
    echo "SKIP: HDFS 不可用，本用例需要 3、4 号模块就绪。" >&2
    exit 1
fi

echo "== 1. 输入不存在时 run.sh 必须失败 =="
expect_nonzero "输入路径不存在" \
    bash "${APP_DIR}/run.sh" "${HDFS_INPUT_ROOT:-/project/input}/wordcount-does-not-exist" "${OUTPUT_ROOT}/never"

echo "== 2. 输出已存在时 run.sh 必须失败，且不覆盖旧数据 =="
# 准备一个已存在的输出目录（内容由本脚本创建，结束时清理）。
"${HDFS_BIN}" dfs -mkdir -p "${GUARD_DIR}"
printf 'guard\t1\n' > "${SCRIPT_DIR}/build/guard-marker.txt"
"${HDFS_BIN}" dfs -put -f "${SCRIPT_DIR}/build/guard-marker.txt" "${GUARD_DIR}/part-r-00000"
expect_nonzero "输出目录已存在" \
    bash "${APP_DIR}/run.sh" "${INPUT_DIR_HDFS}" "${GUARD_DIR}"
if "${HDFS_BIN}" dfs -test -e "${GUARD_DIR}/part-r-00000"; then
    ok "旧输出未被删除"
else
    ng "旧输出被覆盖或删除"
fi
"${HDFS_BIN}" dfs -rm -r -f "${GUARD_DIR}" >/dev/null 2>&1 || true
rm -f "${SCRIPT_DIR}/build/guard-marker.txt"

echo "== 3. 核对不存在的输出时 verify.sh 必须失败 =="
expect_nonzero "输出目录不存在" \
    bash "${APP_DIR}/verify.sh" "${OUTPUT_ROOT}/verify-does-not-exist"

echo "== 4. 用错误的预期核对时必须失败 =="
WRONG_EXPECTED="${SCRIPT_DIR}/build/wrong-expected.tsv"
printf 'hadoop\t999\n' > "${WRONG_EXPECTED}"
TARGET_OUTPUT="${OUTPUT_ROOT}/run-001"
if "${HDFS_BIN}" dfs -test -d "${TARGET_OUTPUT}"; then
    export WORDCOUNT_EXPECTED="${WRONG_EXPECTED}"
    expect_nonzero "错误预期应被拒绝" bash "${APP_DIR}/verify.sh" "${TARGET_OUTPUT}"
    unset WORDCOUNT_EXPECTED
else
    echo "  SKIP  还没有 ${TARGET_OUTPUT}，先跑一次固定小样例再复测本项"
fi
rm -f "${WRONG_EXPECTED}"

echo
echo "结果: PASS=${PASS} FAIL=${FAIL}"
if [ "${FAIL}" -gt 0 ]; then
    echo "FAILURE CASES FAIL"
    exit 1
fi
echo "FAILURE CASES PASS"
