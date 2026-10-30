#!/usr/bin/env bash
# 3 号 HDFS 测试的共用函数。
# 只在已加载 HDFS 配置的集群节点（master 或 worker）容器内使用，不要在电脑终端直接执行。
# 由各 check-*.sh 用 `. common.sh` 引入；脚本自行定位所在目录，可从任意当前目录调用。

set -euo pipefail

HDFS_TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HDFS_FIXTURES="$HDFS_TEST_DIR/fixtures"
HDFS_RUNTIME="$HDFS_TEST_DIR/runtime"

# 公共接口固定值，取自 .development 与 docs/interfaces.md
EXPECTED_DEFAULT_FS="hdfs://master:9000"
EXPECTED_NAMENODE_DIR="/var/lib/hadoop/hdfs/namenode"
EXPECTED_DATANODE_DIR="/var/lib/hadoop/hdfs/datanode"
EXPECTED_REPLICATION="2"
EXPECTED_LIVE_DATANODES="2"

# HDFS 路径（interfaces.md：输入根 /project/input）
HDFS_DEMO_DIR="/project/input/hdfs-demo"
HDFS_SAMPLE_001="$HDFS_DEMO_DIR/sample-001.txt"
HDFS_SAMPLE_002="$HDFS_DEMO_DIR/sample-002.txt"
HDFS_PERSIST_FILE="$HDFS_DEMO_DIR/persist-001.txt"
HDFS_LARGE_FILE="$HDFS_DEMO_DIR/large-001.txt"

info() { printf '[hdfs] %s\n' "$*"; }
ok() { printf '[hdfs] PASS: %s\n' "$*"; }
die() {
    printf '[hdfs] FAIL: %s\n' "$*" >&2
    exit 1
}

require_hdfs() {
    command -v hdfs >/dev/null 2>&1 || die 'hdfs 命令不可用：本脚本必须在已加载 HDFS 配置的集群节点内执行'
    [[ -n "${HADOOP_CONF_DIR:-}" ]] || die 'HADOOP_CONF_DIR 未设置：容器内未加载 Hadoop 配置'
}

# 读取节点实际生效的配置值（不是读文件，而是 hdfs 自己解析后的结果）
conf_key() { hdfs getconf -confKey "$1" 2>/dev/null | tr -d '\r'; }

# 归一化目录配置：去掉 file: 前缀与末尾斜杠，便于和 .development 的值直接比较
normalize_dir() {
    local value="$1"
    value="${value#file:}"
    value="${value#//}"
    printf '%s' "${value%/}"
}

# 输出当前 Live DataNode，每行「IP hostname」；只取 Live datanodes 段，排除 Dead / Decommissioning
# 行首可能有空格（各 Hadoop 版本缩进不一致），所以正则不锚定行首
hdfs_live_nodes() {
    hdfs dfsadmin -report 2>/dev/null | tr -d '\r' | awk '
        /^[[:space:]]*Live datanodes \(/ { inlive = 1; next }
        /^[[:space:]]*(Dead datanodes|Decommissioning datanodes|Entering maintenance)/ { inlive = 0 }
        inlive && /^[[:space:]]*Name: / { ip = $2; sub(/:.*/, "", ip); next }
        inlive && /^[[:space:]]*Hostname: / { print ip, $2 }
    '
}

# 列出某个 HDFS 文件的所有块 ID，每行一个
hdfs_block_ids() {
    local path="$1"
    hdfs fsck "$path" -files -blocks 2>/dev/null | tr -d '\r' |
        awk '/^[[:space:]]*[0-9]+\. (BP-|blk_)/ { id = $2; sub(/\.$/, "", id); print id }'
}

# 统计行数，无输出时返回 0 而不是非零（grep -c 在零匹配时退出码为 1）
count_lines() { awk 'END { print NR }'; }
