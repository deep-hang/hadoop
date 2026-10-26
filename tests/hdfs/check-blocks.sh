#!/usr/bin/env bash
# check-blocks.sh —— 用 fsck 证明：文件健康、块数正确、每个块恰好 2 个副本且分别落在两个 Worker 上。
# 执行位置：master 容器内。默认检查 sample-001，也可传入其他 HDFS 路径（如多块演示的大文件）。
# 用法：bash /workspace/tests/hdfs/check-blocks.sh [hdfs 路径]

set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/common.sh"

require_hdfs

target="${1:-$HDFS_SAMPLE_001}"
hdfs dfs -test -e "$target" || die "HDFS 中不存在 $target，请先执行 check-readwrite.sh"

info "hdfs fsck $target -files -blocks -locations"
fsck_out="$(hdfs fsck "$target" -files -blocks -locations 2>&1 || true)"
printf '%s\n' "$fsck_out" | sed 's/^/    /'

# 1. 总体健康状况
printf '%s\n' "$fsck_out" | grep -q 'Status: HEALTHY' ||
    die 'fsck 状态不是 HEALTHY（可能有损坏或缺失的块）'
ok 'fsck 状态 HEALTHY'

# 缺块 / 欠副本必须为 0；不同 Hadoop 版本措辞略有差异，两种写法都接受
expect_zero() {
    local label="$1" line
    line="$(printf '%s\n' "$fsck_out" | grep -E "^${label}:" | head -n 1 || true)"
    [[ -n "$line" ]] || {
        info "fsck 输出未包含「$label」，跳过该项"
        return 0
    }
    printf '%s' "$line" | grep -Eq ':[[:space:]]*0$' || die "「$line」应为 0"
    ok "$line"
}
expect_zero 'Missing blocks'
expect_zero 'Under-replicated blocks'
expect_zero 'Under replicated blocks'
expect_zero 'Corrupt blocks'

# 2. 当前 Live DataNode 的 IP 清单
live_nodes="$(hdfs_live_nodes)"
live_ip_count="$(printf '%s\n' "$live_nodes" | count_lines)"
[[ "$live_ip_count" -eq "$EXPECTED_LIVE_DATANODES" ]] ||
    die "Live DataNode 数量为 $live_ip_count，期望 $EXPECTED_LIVE_DATANODES，先跑 check-datanodes.sh"

live_ips="$(printf '%s\n' "$live_nodes" | awk '{ print $1 }' | sort -u)"

# 3. 逐个块核对副本位置
block_lines="$(printf '%s\n' "$fsck_out" | grep -E '^[0-9]+\. (BP-|blk_)' || true)"
[[ -n "$block_lines" ]] || die "fsck 输出中没有块信息：$target"

block_index=0
while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    block_index=$((block_index + 1))

    replica_ips="$(printf '%s\n' "$line" |
        grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]+' |
        cut -d: -f1 | sort -u || true)"
    [[ -n "$replica_ips" ]] ||
        die "第 $block_index 个块没有副本位置信息（fsck 是否带 -locations？）：$line"

    replica_count="$(printf '%s\n' "$replica_ips" | count_lines)"
    [[ "$replica_count" -eq "$EXPECTED_REPLICATION" ]] ||
        die "第 $block_index 个块有 $replica_count 个副本位置，期望 $EXPECTED_REPLICATION：$line"

    while IFS= read -r ip; do
        printf '%s\n' "$live_ips" | grep -qx "$ip" ||
            die "第 $block_index 个块的副本位于 $ip，但该地址不是当前 Live DataNode"
    done <<<"$replica_ips"

    info "块 $block_index 副本位置：$(printf '%s ' $replica_ips)"
done <<<"$block_lines"

# 4. 两个 Worker 都在副本位置里出现（单块文件即两份副本，正好覆盖两个 Worker）
[[ "$block_index" -ge 1 ]] || die '没有解析到任何块'
info 'Live DataNode 与 IP 对应关系：'
printf '%s\n' "$live_nodes" | sed 's/^/    /'
printf '%s\n' "$live_nodes" | awk '{ print $2 }' | grep -qw worker1 ||
    die '副本位置中没有 worker1'
printf '%s\n' "$live_nodes" | awk '{ print $2 }' | grep -qw worker2 ||
    die '副本位置中没有 worker2'

ok "共 $block_index 个块，每个块 $EXPECTED_REPLICATION 个副本，覆盖 worker1 与 worker2"
printf 'HDFS_BLOCKS_PASS\n'
