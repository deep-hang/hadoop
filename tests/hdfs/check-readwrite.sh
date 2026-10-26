#!/usr/bin/env bash
# check-readwrite.sh —— 用固定输入验证 HDFS 的 mkdir / put / ls / cat / get 全链路，并逐字节比对内容。
# 执行位置：master 容器内。可重复执行：同名文件会被固定输入覆盖，保证结果可复现。
# 用法：bash /workspace/tests/hdfs/check-readwrite.sh

set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/common.sh"

require_hdfs

fixture="$HDFS_FIXTURES/sample-001.txt"
[[ -f "$fixture" ]] || die "缺少固定输入 $fixture"

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

info "创建目录 $HDFS_DEMO_DIR"
hdfs dfs -mkdir -p "$HDFS_DEMO_DIR"

info "上传 $fixture → $HDFS_SAMPLE_001"
hdfs dfs -put -f "$fixture" "$HDFS_SAMPLE_001"

hdfs dfs -test -e "$HDFS_SAMPLE_001" || die "上传后 HDFS 中不存在 $HDFS_SAMPLE_001"

info 'hdfs dfs -ls：'
hdfs dfs -ls "$HDFS_SAMPLE_001" | sed 's/^/    /'

expected_size="$(stat -c %s "$fixture")"
remote_size="$(hdfs dfs -stat '%b' "$HDFS_SAMPLE_001" | tr -d '\r')"
[[ "$remote_size" == "$expected_size" ]] ||
    die "HDFS 中文件大小 ${remote_size} 字节，固定输入 ${expected_size} 字节"
ok "文件大小一致：${remote_size} 字节"

remote_repl="$(hdfs dfs -stat '%r' "$HDFS_SAMPLE_001" | tr -d '\r')"
[[ "$remote_repl" == "$EXPECTED_REPLICATION" ]] ||
    die "文件副本数为 $remote_repl，期望 $EXPECTED_REPLICATION"
ok "文件副本数为 $remote_repl"

hdfs dfs -cat "$HDFS_SAMPLE_001" >"$workdir/cat.txt"
cmp -s "$fixture" "$workdir/cat.txt" || die 'hdfs dfs -cat 的内容与固定输入不一致'
ok "cat 内容与固定输入逐字节一致"

hdfs dfs -get -f "$HDFS_SAMPLE_001" "$workdir/get.txt"
cmp -s "$fixture" "$workdir/get.txt" || die 'hdfs dfs -get 取回的内容与固定输入不一致'
ok "get 取回的内容与固定输入逐字节一致"

# 再上传一个不同内容的固定输入，供重复演示使用（不覆盖 sample-001）
if [[ -f "$HDFS_FIXTURES/sample-002.txt" ]]; then
    hdfs dfs -put -f "$HDFS_FIXTURES/sample-002.txt" "$HDFS_SAMPLE_002"
    hdfs dfs -test -e "$HDFS_SAMPLE_002" || die "上传后 HDFS 中不存在 $HDFS_SAMPLE_002"
    ok "第二个固定输入已就位：$HDFS_SAMPLE_002"
fi

info '目录清单：'
hdfs dfs -ls "$HDFS_DEMO_DIR" | sed 's/^/    /'

printf 'HDFS_READWRITE_PASS\n'
