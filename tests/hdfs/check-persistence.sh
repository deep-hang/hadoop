#!/usr/bin/env bash
# check-persistence.sh —— 证明「重启不重新格式化、文件仍在」：重启前记录指纹，重启后比对。
# 执行位置：master 容器内，两次执行之间由 2 号执行重启（down 不删卷 → up -d）。
# 用法：
#   bash /workspace/tests/hdfs/check-persistence.sh record   # 重启前
#   ... 2 号重启集群，确认没有删卷 ...
#   bash /workspace/tests/hdfs/check-persistence.sh verify   # 重启后

set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/common.sh"

action="${1:-}"
case "$action" in
    record | verify) ;;
    *)
        echo 'Usage: bash check-persistence.sh {record|verify}' >&2
        exit 2
        ;;
esac

require_hdfs
mkdir -p "$HDFS_RUNTIME"
record_file="$HDFS_RUNTIME/persistence-001.env"

# 指纹 = 内容 sha256 + 块 ID 列表
# 只比内容无法区分「原文件还在」和「重新上传了一份一样的」，加上块 ID 才能证明是同一份数据
snapshot() {
    local sha blocks
    hdfs dfs -test -e "$HDFS_PERSIST_FILE" ||
        die "HDFS 中不存在 $HDFS_PERSIST_FILE（文件已丢，或从未上传）"
    sha="$(hdfs dfs -cat "$HDFS_PERSIST_FILE" | sha256sum | cut -d' ' -f1)"
    blocks="$(hdfs_block_ids "$HDFS_PERSIST_FILE" | paste -sd, -)"
    [[ -n "$blocks" ]] || die "无法从 fsck 取到 $HDFS_PERSIST_FILE 的块 ID"
    printf 'SHA256=%s\nBLOCKS=%s\n' "$sha" "$blocks"
}

if [[ "$action" == record ]]; then
    info "上传固定输入 $HDFS_FIXTURES/sample-001.txt → $HDFS_PERSIST_FILE"
    hdfs dfs -mkdir -p "$HDFS_DEMO_DIR"
    hdfs dfs -put -f "$HDFS_FIXTURES/sample-001.txt" "$HDFS_PERSIST_FILE"

    {
        snapshot
        printf 'RECORDED_AT=%s\nRECORDED_BY=%s\n' "$(date -Is)" "$(hostname)"
    } >"$record_file"

    info '重启前指纹：'
    sed 's/^/    /' "$record_file"
    ok "已记录到 $record_file（在 /workspace 内，容器重建后仍在）"
    echo '下一步：让 2 号用不删卷的方式重启集群，再执行 verify'
    printf 'HDFS_PERSISTENCE_RECORDED\n'
    exit 0
fi

[[ -f "$record_file" ]] || die "缺少 $record_file：请先在重启前执行 record"
before="$(grep -E '^(SHA256|BLOCKS)=' "$record_file")"
after="$(snapshot)"

info '重启前：'
printf '%s\n' "$before" | sed 's/^/    /'
info '重启后：'
printf '%s\n' "$after" | sed 's/^/    /'

[[ "$before" == "$after" ]] ||
    die '重启前后内容 sha256 或块 ID 不一致：文件丢失，或 NameNode 元数据没有持久化'

ok '重启后文件仍可读，内容与块 ID 均未变化（未重新格式化）'
printf 'HDFS_PERSISTENCE_PASS\n'
