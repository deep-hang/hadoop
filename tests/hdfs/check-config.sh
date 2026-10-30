#!/usr/bin/env bash
# check-config.sh —— 核对节点实际加载的 HDFS 配置是否等于公共接口约定值。
# 执行位置：master 容器内（worker 也可，但以 master 的 NameNode 为准）。
# 用法：bash /workspace/tests/hdfs/check-config.sh

set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/common.sh"

require_hdfs
info "HADOOP_CONF_DIR=$HADOOP_CONF_DIR"

for file in core-site.xml hdfs-site.xml; do
    [[ -f "$HADOOP_CONF_DIR/$file" ]] ||
        die "$HADOOP_CONF_DIR 下缺少 $file：2 号还没把 3 号的配置挂进容器"
done

expect_value() {
    local key="$1" expected="$2" actual
    actual="$(conf_key "$key")"
    [[ "$actual" == "$expected" ]] || die "$key=$actual，期望 $expected"
    ok "$key=$actual"
}

expect_dir() {
    local key="$1" expected="$2" actual
    actual="$(normalize_dir "$(conf_key "$key")")"
    [[ "$actual" == "$expected" ]] ||
        die "$key=$actual，期望 $expected（hadoop-node.sh 启动时会做同样的比对）"
    ok "$key=$actual"
}

expect_value fs.defaultFS "$EXPECTED_DEFAULT_FS"
expect_dir dfs.namenode.name.dir "$EXPECTED_NAMENODE_DIR"
expect_dir dfs.datanode.data.dir "$EXPECTED_DATANODE_DIR"
expect_value dfs.replication "$EXPECTED_REPLICATION"

# 安全模式等待时间只做提示，不作为失败条件：不影响读写正确性
safemode_extension="$(conf_key dfs.namenode.safemode.extension)"
info "dfs.namenode.safemode.extension=${safemode_extension:-未设置（默认 30000 毫秒）}"

# 数据目录必须落在持久卷内，否则容器重建即丢
for dir in "$EXPECTED_NAMENODE_DIR" "$EXPECTED_DATANODE_DIR"; do
    case "$dir" in
        /var/lib/hadoop/*) ;;
        *) die "$dir 不在持久卷 /var/lib/hadoop 下，重启会丢数据" ;;
    esac
done

printf 'HDFS_CONFIG_PASS\n'
