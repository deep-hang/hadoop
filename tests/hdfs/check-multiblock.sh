#!/usr/bin/env bash
# check-multiblock.sh —— 可选：生成大于块大小的输入，证明「一个文件被切成多个块、每块两份副本」。
# 只在 PPT/视频要讲「多数据块」时用；默认块大小 128 MB，默认生成 140 MB。
# 执行位置：master 容器内。
# 用法：bash /workspace/tests/hdfs/check-multiblock.sh [大小 MB]

set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/common.sh"

require_hdfs

size_mb="${1:-140}"
[[ "$size_mb" =~ ^[0-9]+$ ]] || die "大小必须是整数 MB：$size_mb"

block_size="$(conf_key dfs.blocksize)"
block_size="${block_size:-134217728}"
# 块数按向上取整算：140 MB / 128 MB 实际是 2 块，用向下取整会误判成 1 块
size_bytes=$((size_mb * 1024 * 1024))
expected_min_blocks=$(((size_bytes + block_size - 1) / block_size))
((expected_min_blocks >= 2)) ||
    die "输入 ${size_mb} MB 只能切出 1 个块（当前 dfs.blocksize=${block_size} 字节），改用 140 这类大于块大小的值"

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

info "生成 ${size_mb} MB 测试输入（dfs.blocksize=${block_size} 字节）"
dd if=/dev/zero bs=1M count="$size_mb" status=none | tr '\0' 'a' >"$workdir/large.txt"
ls -l "$workdir/large.txt" | sed 's/^/    /'

hdfs dfs -mkdir -p "$HDFS_DEMO_DIR"
info "上传 → $HDFS_LARGE_FILE"
hdfs dfs -put -f "$workdir/large.txt" "$HDFS_LARGE_FILE"

info 'hdfs fsck（只看块数）：'
blocks="$(hdfs_block_ids "$HDFS_LARGE_FILE")"
block_count="$(printf '%s\n' "$blocks" | count_lines)"
[[ "$block_count" -ge 2 ]] ||
    die "只切出 $block_count 个块，期望至少 2 个，无法演示多数据块"
ok "文件被切成 $block_count 个块"

# 复用 check-blocks.sh 核对「每块 2 副本、覆盖两个 Worker」
bash "$HDFS_TEST_DIR/check-blocks.sh" "$HDFS_LARGE_FILE"

info "演示完成后可清理（双副本约占 $((size_mb * 2)) MB）：hdfs dfs -rm -f $HDFS_LARGE_FILE"
printf 'HDFS_MULTIBLOCK_PASS\n'
