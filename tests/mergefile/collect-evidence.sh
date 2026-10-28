#!/usr/bin/env bash
# 收集 MergeFile 双 Worker 演示的证据。
#
# 用法（在装有 Docker Compose 的电脑上）：
#   bash tests/mergefile/collect-evidence.sh <compose 项目名>
#
# 证据分四部分：
#   1. 两个 DataNode 与两个 NodeManager 的注册状态
#   2. 输入文件的块位置（每个文件的块同时存放在两个 DataNode 上）
#   3. YARN application 列表与 ResourceManager 的容器分配记录
#   4. 每个节点上实际跑过的容器与任务类型
set -uo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$TEST_DIR/../.." && pwd)"
FIXTURE="$REPO_DIR/tests/common/fixtures/cluster/compose.yaml"

PROJECT="${1:-}"
[[ -n "$PROJECT" ]] || { echo "用法: bash $(basename "$0") <compose 项目名>" >&2; exit 2; }

COMPOSE=(docker compose -p "$PROJECT" -f "$FIXTURE")

heading() {
    echo
    echo "================================================================"
    echo "$*"
    echo "================================================================"
}

heading "1. 集群节点：两个 DataNode + 两个 NodeManager"
"${COMPOSE[@]}" exec -T master bash -c \
    'hdfs dfsadmin -report 2>/dev/null | grep -E "^(Live datanodes|Name: |Hostname: |Num of Blocks: )"; echo; yarn node -list 2>/dev/null'

heading "2. 多文件输入的块位置：每个文件的块同时存放在两个 DataNode 上"
"${COMPOSE[@]}" exec -T master bash -c \
    'hdfs fsck /project/input/mergefile-multi -files -blocks -locations 2>/dev/null | sed -n "1,26p"'

heading "3. YARN 作业列表"
"${COMPOSE[@]}" exec -T master bash -c 'yarn application -list -appStates ALL 2>/dev/null'

heading "4. ResourceManager 的容器分配记录：容器 -> 节点"
"${COMPOSE[@]}" logs --no-color master 2>/dev/null \
    | grep -oE "Assigned container container_[0-9_]+ of capacity .* on host [a-z0-9]+" \
    | sed -E 's/Assigned container (container_[0-9_]+) of capacity .* on host ([a-z0-9]+)/\1 -> \2/' \
    | sort -u

heading "5. 每个节点上实际跑过的容器与任务类型"
# 容器的工作目录就是 /workspace，用相对路径传脚本，避免 Windows 上的 Git Bash
# 把 /workspace/... 改写成 Windows 路径。
for worker in worker1 worker2; do
    "${COMPOSE[@]}" exec -T "$worker" bash tests/mergefile/collect-node-evidence.sh
done

heading "6. 结果文件与它的块位置"
"${COMPOSE[@]}" exec -T master bash -c \
    'hdfs dfs -cat /project/output/mergefile/run-002/merged.txt; echo; hdfs fsck /project/output/mergefile/run-002 -files -blocks -locations 2>/dev/null | sed -n "1,12p"'
