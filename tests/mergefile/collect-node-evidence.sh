#!/usr/bin/env bash
# 打印本节点上参与 MergeFile 作业的容器，用于证明两个 worker 都有计算参与。
#
# 用法（在集群的任一节点容器内执行）：
#   bash /workspace/tests/mergefile/collect-node-evidence.sh [application_id ...]
#
# 任务类型从容器自己的 syslog 判断，不靠容器编号猜测：
#   MRAppMaster          -> ApplicationMaster
#   MapTask metrics ...  -> Map 任务
#   ReduceTask metrics.. -> Reduce 任务
#
# 输出格式：application_id  container_id  任务类型  所在节点
set -uo pipefail

HOST_NAME="$(hostname)"
LOG_ROOT="/opt/hadoop/logs/userlogs"

application_ids=("$@")
if [[ "${#application_ids[@]}" -eq 0 ]]; then
    while IFS= read -r application_id; do
        [[ -n "$application_id" ]] && application_ids+=("$application_id")
    done < <(ls -1 "$LOG_ROOT" 2>/dev/null | grep '^application_' || true)
fi

echo "--- 节点 $HOST_NAME 上参与 MergeFile 作业的容器 ---"
found=0
for application_id in "${application_ids[@]}"; do
    application_dir="$LOG_ROOT/$application_id"
    [[ -d "$application_dir" ]] || continue
    for container_dir in "$application_dir"/container_*; do
        [[ -d "$container_dir" ]] || continue
        container_id="$(basename "$container_dir")"
        task_type="未知"
        if grep -q "MRAppMaster" "$container_dir/syslog" 2>/dev/null; then
            task_type="ApplicationMaster"
        elif grep -q "ReduceTask metrics system started" "$container_dir/syslog" 2>/dev/null; then
            task_type="Reduce 任务"
        elif grep -q "MapTask metrics system started" "$container_dir/syslog" 2>/dev/null; then
            task_type="Map 任务"
        fi
        echo "$application_id  $container_id  $task_type  所在节点=$HOST_NAME"
        found=1
    done
done
if [[ "$found" -eq 0 ]]; then
    echo "（本节点没有 MergeFile 作业的容器）"
fi
