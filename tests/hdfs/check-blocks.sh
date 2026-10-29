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

# 1. 总体健康状况（摘要行的行首可能有空格）
printf '%s\n' "$fsck_out" | tr -d '\r' | grep -Eq '^[[:space:]]*Status:[[:space:]]*HEALTHY' ||
    die 'fsck 状态不是 HEALTHY（可能有损坏或缺失的块）'
ok 'fsck 状态 HEALTHY'

# 缺块 / 欠副本 / 损坏块必须为 0。
# 真实 fsck 摘要行有三个坑，不能锚定行首也不能要求行尾是 0：
#   1) 行首带一个空格：  " Under-replicated blocks:\t0 (0.0 %)"
#   2) 冒号后是制表符；
#   3) 部分计数后面还跟着百分比。
# 所以改为「字段名 + 冒号 + 该行第一个整数」，与缩进、分隔符、后续内容无关。
# 注意：这样能跳过 "Missing blocks (with replication factor 1):" 这类同前缀字段，
# 因为字段名后面紧跟的是左括号而不是冒号。
field_count=0
skipped=()
expect_zero() {
    local label="$1" value
    value="$(printf '%s\n' "$fsck_out" | tr -d '\r' |
        sed -n -E "s/^[[:space:]]*${label}[[:space:]]*:[^0-9]*([0-9]+).*/\1/p" | head -n 1)"
    if [[ -z "$value" ]]; then
        skipped+=("$label")
        return 0
    fi
    field_count=$((field_count + 1))
    [[ "$value" == '0' ]] || die "「${label}」= ${value}，期望 0"
    ok "${label} = ${value}"
}
expect_zero 'Missing blocks'
expect_zero 'Under-replicated blocks'
expect_zero 'Corrupt blocks'

if ((${#skipped[@]} > 0)); then
    info "以下字段本次 fsck 输出里没有出现（该版本可能只在非 0 时打印）：${skipped[*]}"
fi
((field_count > 0)) ||
    die 'fsck 摘要计数一条都没识别出来：输出格式与预期差异太大，请把上面的原始输出发给 3 号'

# 2. 当前 Live DataNode 的 IP 清单
live_nodes="$(hdfs_live_nodes)"
live_ip_count="$(printf '%s\n' "$live_nodes" | count_lines)"
[[ "$live_ip_count" -eq "$EXPECTED_LIVE_DATANODES" ]] ||
    die "Live DataNode 数量为 $live_ip_count，期望 $EXPECTED_LIVE_DATANODES，先跑 check-datanodes.sh"

live_ips="$(printf '%s\n' "$live_nodes" | awk '{ print $1 }' | sort -u)"

# 3. 逐个块核对副本位置（块行同样允许行首空格）
block_lines="$(printf '%s\n' "$fsck_out" | tr -d '\r' | grep -E '^[[:space:]]*[0-9]+\. (BP-|blk_)' || true)"
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
