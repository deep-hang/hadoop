#!/usr/bin/env bash
#
# 失败用例：确认“出错时明确失败”，而不是默默返回成功。
#
# 前置条件：HDFS、YARN 已就绪（3、4 号模块），且已执行 build.sh。
# 执行位置：项目根目录。
#   bash tests/wordcount/check-failure-cases.sh
#
# 覆盖五项：
#   1. 输入不存在          -> run.sh 必须非 0，且不留下输出目录
#   2. 输出已存在          -> run.sh 必须非 0，且不删除已有数据
#   3. 核对不存在的输出     -> verify.sh 必须非 0
#   4. 用错误的预期去核对   -> verify.sh 必须非 0
#   5. 结果里混入格式错误的行 -> verify.sh 必须非 0（次数非整数、多出残行）
#
# 目录隔离（本脚本不乱删东西）：
#   - 本地临时文件全部放在本次运行独占的 mktemp -d 目录里，结束只删这一个目录；
#   - HDFS 上的测试目录名带时间戳 + 进程号 + 随机数，每次都是新目录，
#     创建前还会确认它事先不存在，结束后只删本次创建的那一个。
#   所以往 ${HDFS_OUTPUT_ROOT}/wordcount 里预置的文件不会被动到。
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
APP_DIR="${PROJECT_ROOT}/apps/wordcount"

# shellcheck disable=SC1091
. "${PROJECT_ROOT}/.development"

HADOOP_BIN="${HADOOP_HOME:-/opt/hadoop}/bin/hadoop"
HDFS_BIN="${HADOOP_HOME:-/opt/hadoop}/bin/hdfs"
HDFS_URI="${HDFS_URI:-hdfs://master:9000}"
INPUT_DIR_HDFS="${HDFS_INPUT_ROOT:-/project/input}/wordcount"
OUTPUT_ROOT="${HDFS_OUTPUT_ROOT:-/project/output}/wordcount"

# 本次运行的唯一标识：同一秒内重复执行、并行执行都不会撞名。
RUN_ID="$(date +%Y%m%d-%H%M%S)-$$-${RANDOM:-0}"

# 本地工作目录：只本脚本用，退出时整体删除。
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/wordcount-failure-cases.XXXXXX")" || {
    echo "FAIL: 无法创建临时目录" >&2
    exit 1
}

GUARD_DIR="${OUTPUT_ROOT}/failure-case-guard-${RUN_ID}"    # 本脚本自己造的“已存在输出”
NEVER_DIR="${OUTPUT_ROOT}/failure-case-never-${RUN_ID}"    # 本该永远不被创建的输出
MISS_DIR="${OUTPUT_ROOT}/failure-case-missing-${RUN_ID}"   # 本该不存在的输出
GUARD_CREATED=0

cleanup() {
    # 只删本次自己创建的路径：名字里带 RUN_ID，正常情况下不可能属于别人。
    if [ "${GUARD_CREATED}" = "1" ] && [ -n "${GUARD_DIR}" ]; then
        "${HDFS_BIN}" dfs -rm -r -f "${GUARD_DIR}" >/dev/null 2>&1 || true
    fi
    if [ -n "${NEVER_DIR}" ]; then
        "${HDFS_BIN}" dfs -rm -r -f "${NEVER_DIR}" >/dev/null 2>&1 || true
    fi
    if [ -n "${WORK_DIR}" ] && [ -d "${WORK_DIR}" ]; then
        rm -rf "${WORK_DIR}" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT

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

echo "本次运行标识: ${RUN_ID}"
echo "本地临时目录: ${WORK_DIR}"

echo "== 1. 输入不存在时 run.sh 必须失败 =="
expect_nonzero "输入路径不存在" \
    bash "${APP_DIR}/run.sh" "${HDFS_INPUT_ROOT:-/project/input}/wordcount-does-not-exist-${RUN_ID}" "${NEVER_DIR}"
if "${HDFS_BIN}" dfs -test -e "${NEVER_DIR}" 2>/dev/null; then
    ng "失败的作业不应留下输出目录 ${NEVER_DIR}"
else
    ok "没有留下输出目录"
fi

echo "== 2. 输出已存在时 run.sh 必须失败，且不覆盖旧数据 =="
# 用一个全新的、事先不存在的目录，避免碰到别人预置的数据。
if "${HDFS_BIN}" dfs -test -e "${GUARD_DIR}" 2>/dev/null; then
    echo "FAIL: 目标目录竟然已存在，拒绝继续（避免动到别人的数据）: ${GUARD_DIR}" >&2
    exit 1
fi
if ! "${HDFS_BIN}" dfs -mkdir -p "${GUARD_DIR}" >/dev/null 2>&1; then
    echo "FAIL: 无法创建测试目录 ${GUARD_DIR}" >&2
    exit 1
fi
GUARD_CREATED=1
printf 'guard\t1\n' > "${WORK_DIR}/guard-marker.txt"
"${HDFS_BIN}" dfs -put -f "${WORK_DIR}/guard-marker.txt" "${GUARD_DIR}/part-r-00000" >/dev/null 2>&1
expect_nonzero "输出目录已存在" \
    bash "${APP_DIR}/run.sh" "${INPUT_DIR_HDFS}" "${GUARD_DIR}"
if "${HDFS_BIN}" dfs -test -e "${GUARD_DIR}/part-r-00000"; then
    ok "旧输出未被删除"
else
    ng "旧输出被覆盖或删除"
fi

echo "== 3. 核对不存在的输出时 verify.sh 必须失败 =="
expect_nonzero "输出目录不存在" \
    bash "${APP_DIR}/verify.sh" "${MISS_DIR}"

echo "== 4. 用错误的预期核对时必须失败 =="
WRONG_EXPECTED="${WORK_DIR}/wrong-expected.tsv"
printf 'hadoop\t999\n' > "${WRONG_EXPECTED}"
TARGET_OUTPUT="${OUTPUT_ROOT}/run-001"
if "${HDFS_BIN}" dfs -test -d "${TARGET_OUTPUT}" 2>/dev/null; then
    export WORDCOUNT_EXPECTED="${WRONG_EXPECTED}"
    expect_nonzero "错误预期应被拒绝" bash "${APP_DIR}/verify.sh" "${TARGET_OUTPUT}"
    unset WORDCOUNT_EXPECTED
else
    echo "  SKIP  还没有 ${TARGET_OUTPUT}，先跑一次固定小样例再复测本项"
fi

echo "== 5. 结果里混入格式错误的行时 verify.sh 必须失败 =="
# 造一份“看起来像结果、但有一行不合法”的输出，确认 verify.sh 不会把它当成通过。
BAD_OUT="${WORK_DIR}/bad-output"
mkdir -p "${BAD_OUT}"
printf 'hadoop\t2\nhello\t2\nworld\tnot-a-number\n' > "${BAD_OUT}/part-r-00000"
expect_nonzero "次数不是整数时拒绝通过" \
    env WORDCOUNT_LOCAL=1 bash "${APP_DIR}/verify.sh" "${BAD_OUT}"

BAD_OUT2="${WORK_DIR}/bad-output-2"
mkdir -p "${BAD_OUT2}"
printf 'hadoop\t2\nhello\t2.9\nworld\t1\nextra-line-without-count\n' > "${BAD_OUT2}/part-r-00000"
expect_nonzero "次数写成小数且多出残行时拒绝通过" \
    env WORDCOUNT_LOCAL=1 bash "${APP_DIR}/verify.sh" "${BAD_OUT2}"

echo
echo "结果: PASS=${PASS} FAIL=${FAIL}"
if [ "${FAIL}" -gt 0 ]; then
    echo "FAILURE CASES FAIL"
    exit 1
fi
echo "FAILURE CASES PASS"
