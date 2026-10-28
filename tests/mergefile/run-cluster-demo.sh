#!/usr/bin/env bash
# MergeFile 双 Worker 演示：在真实三节点集群上跑一次作业并收集证据。
#
# 用法：
#   bash tests/mergefile/run-cluster-demo.sh            # 起集群 -> 跑作业 -> 收证据 -> 拆集群
#   bash tests/mergefile/run-cluster-demo.sh --keep     # 跑完后不拆集群，方便继续查看
#   bash tests/mergefile/run-cluster-demo.sh --job-only # 只跑作业部分（已经在 master 容器内时用）
#
# 集群配置复用 tests/common/fixtures/cluster/（公共验证用配置：master + worker1 + worker2），
# 使用独立的 compose 项目名和独立数据卷，不影响其他人的集群，结束时只清理自己创建的资源。
#
# 演示分两部分：
#   1. 固定小样例：apps/mergefile/input/      -> /project/output/mergefile/run-001，用 verify.sh 核对
#   2. 多文件数据集：tests/mergefile/input-multi/ -> /project/output/mergefile/run-002，
#      用 verify-multi.sh 核对；8 个输入文件让 Map 任务分布在两个 worker 上
#
# 证据由 collect-evidence.sh 收集：节点注册、块位置、作业列表、容器所在节点。
set -uo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$TEST_DIR/../.." && pwd)"
FIXTURE="$REPO_DIR/tests/common/fixtures/cluster/compose.yaml"

KEEP_CLUSTER=0
JOB_ONLY=0
RUN_TESTS=0
for argument in "$@"; do
    case "$argument" in
        --keep) KEEP_CLUSTER=1 ;;
        --job-only) JOB_ONLY=1 ;;
        --tests) RUN_TESTS=1 ;;
        *) echo "用法: bash $(basename "$0") [--keep|--tests]" >&2; exit 2 ;;
    esac
done

# 集群里的工作目录：公共验证配置把仓库挂成只读，编译产物需要写到可写位置
DEMO_ROOT=/tmp/mergefile-demo
APP_DIR="$DEMO_ROOT/apps/mergefile"
TESTS_DIR="$DEMO_ROOT/tests/mergefile"

SMALL_INPUT=/project/input/mergefile
SMALL_OUTPUT=/project/output/mergefile/run-001
MULTI_INPUT=/project/input/mergefile-multi
MULTI_OUTPUT=/project/output/mergefile/run-002

heading() {
    echo
    echo "================================================================"
    echo "$*"
    echo "================================================================"
}

# ---------------------------------------------------------------------------
# 作业部分：在 master 容器内执行
# ---------------------------------------------------------------------------
run_job() {
    heading "步骤 1/3：在 master 容器内准备可写的编译目录"
    rm -rf "$DEMO_ROOT"
    mkdir -p "$DEMO_ROOT"
    cp -r /workspace/apps "$DEMO_ROOT/apps"
    cp -r /workspace/tests "$DEMO_ROOT/tests"
    rm -rf "$DEMO_ROOT/apps/mergefile/build"

    heading "步骤 2/3：编译应用"
    bash "$APP_DIR/build.sh" || return 1

    heading "步骤 3/3：上传两批输入并运行作业"
    echo "--- 固定小样例：$SMALL_INPUT -> $SMALL_OUTPUT ---"
    hdfs dfs -mkdir -p "$SMALL_INPUT"
    hdfs dfs -put "$APP_DIR/input/"*.txt "$SMALL_INPUT"
    bash "$APP_DIR/run.sh" "$SMALL_INPUT" "$SMALL_OUTPUT" || return 1
    bash "$APP_DIR/verify.sh" "$SMALL_OUTPUT" || return 1

    echo "--- 多文件数据集：$MULTI_INPUT -> $MULTI_OUTPUT ---"
    hdfs dfs -mkdir -p "$MULTI_INPUT"
    hdfs dfs -put "$TESTS_DIR/input-multi/"*.txt "$MULTI_INPUT"
    bash "$APP_DIR/run.sh" "$MULTI_INPUT" "$MULTI_OUTPUT" || return 1
    bash "$TESTS_DIR/verify-multi.sh" "$MULTI_OUTPUT" || return 1
    return 0
}

if [[ "$JOB_ONLY" -eq 1 ]]; then
    run_job
    exit $?
fi

# ---------------------------------------------------------------------------
# 集群部分：在有 Docker Compose 的电脑上执行
# ---------------------------------------------------------------------------
command -v docker >/dev/null 2>&1 || { echo "找不到 docker 命令" >&2; exit 3; }
[[ -f "$FIXTURE" ]] || { echo "缺少集群验证配置: $FIXTURE" >&2; exit 3; }

PROJECT="hadoop-mergefile-$(date +%Y%m%d-%H%M%S)-$$"
COMPOSE=(docker compose -p "$PROJECT" -f "$FIXTURE")

cleanup() {
    if [[ "$KEEP_CLUSTER" -eq 1 ]]; then
        echo
        echo "保留集群，可用下面的命令继续查看："
        echo "  docker compose -p $PROJECT -f $FIXTURE ps"
        echo "  docker compose -p $PROJECT -f $FIXTURE logs -f master"
        return
    fi
    echo
    echo "清理集群 $PROJECT ..."
    "${COMPOSE[@]}" down --volumes --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

heading "步骤 0/2：启动隔离的三节点集群（项目名 $PROJECT）"
"${COMPOSE[@]}" config --quiet || exit 3
"${COMPOSE[@]}" run --rm --no-deps master bash scripts/hadoop-node.sh init-namenode || exit 3
"${COMPOSE[@]}" up -d --no-build || exit 3

echo "等待 HDFS/YARN 就绪 ..."
ready=0
for _ in $(seq 1 60); do
    datanodes="$("${COMPOSE[@]}" exec -T master bash -c \
        'hdfs dfsadmin -report 2>/dev/null | sed -n "s/^Live datanodes (\([0-9]*\)).*/\1/p"' | tr -d '\r')"
    nodemanagers="$("${COMPOSE[@]}" exec -T master bash -c \
        'yarn node -list 2>/dev/null | sed -n "s/.*Total Nodes:\([0-9]*\).*/\1/p"' | tr -d '\r')"
    if [[ "${datanodes:-0}" -ge 2 && "${nodemanagers:-0}" -ge 2 ]]; then
        ready=1
        break
    fi
    sleep 5
done
[[ "$ready" -eq 1 ]] || { echo "集群在等待时间内没有就绪" >&2; exit 3; }
echo "集群就绪：2 个 DataNode + 2 个 NodeManager"

"${COMPOSE[@]}" exec -T master bash tests/mergefile/run-cluster-demo.sh --job-only || exit 1

if [[ "$RUN_TESTS" -eq 1 ]]; then
    heading "附加步骤：在真实集群上跑完整的模块测试用例（HDFS 模式）"
    "${COMPOSE[@]}" exec -T master bash tests/mergefile/run-cluster-tests.sh || exit 1
fi

heading "步骤 1/2：收集两个 worker 的数据与计算证据"
bash "$TEST_DIR/collect-evidence.sh" "$PROJECT"
exit 0
