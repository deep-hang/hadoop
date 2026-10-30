#!/usr/bin/env bash
# check-datanodes.sh —— 核对两个 Worker 的 DataNode 是否都已向 NameNode 注册。
# 执行位置：master 容器内。
# 用法：bash /workspace/tests/hdfs/check-datanodes.sh

set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/common.sh"

require_hdfs

hdfs dfsadmin -report >/dev/null 2>&1 ||
    die 'dfsadmin -report 执行失败：NameNode 可能没启动'

nodes="$(hdfs_live_nodes)"
[[ -n "$nodes" ]] || die '没有 Live DataNode：DataNode 全部未注册（检查 worker 服务与卷权限）'

count="$(printf '%s\n' "$nodes" | count_lines)"
info '当前 Live DataNode：'
printf '%s\n' "$nodes" | sed 's/^/    /'

[[ "$count" -eq "$EXPECTED_LIVE_DATANODES" ]] ||
    die "Live DataNode 数量为 $count，期望 $EXPECTED_LIVE_DATANODES（1 Master + 2 Worker，Master 不跑 DataNode）"

printf '%s\n' "$nodes" | grep -qw worker1 ||
    die '未找到 hostname 为 worker1 的 Live DataNode'
printf '%s\n' "$nodes" | grep -qw worker2 ||
    die '未找到 hostname 为 worker2 的 Live DataNode'

ok "worker1、worker2 的 DataNode 均已注册（共 $count 个）"
printf 'HDFS_DATANODES_PASS\n'
