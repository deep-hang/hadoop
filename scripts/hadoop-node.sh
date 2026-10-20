#!/usr/bin/env bash
# Shared foreground launcher; services use the caller's mounted configuration.
set -euo pipefail

usage() { echo 'Usage: bash scripts/hadoop-node.sh {init-namenode|master|worker}' >&2; exit 2; }
[[ $# -eq 1 ]] || usage
role="$1"
case "$role" in init-namenode|master|worker) ;; *) usage ;; esac

check_directory() {
    local property="$1" expected="$2" configured
    configured="$(hdfs getconf -confKey "$property")"
    case "$configured" in
        "$expected"|"file:$expected"|"file://$expected") ;;
        *) echo "Configuration mismatch: $property=$configured; expected $expected" >&2; exit 1 ;;
    esac
}
if [[ "$role" == init-namenode || "$role" == master ]]; then
    check_directory dfs.namenode.name.dir "$HDFS_NAMENODE_DIR"
    if [[ "$role" == init-namenode ]]; then
        mkdir -p "$HDFS_NAMENODE_DIR"
        if [[ -f "$HDFS_NAMENODE_DIR/current/VERSION" ]]; then
            echo 'NameNode already initialized; preserving existing data.'
            exit 0
        fi
        if [[ -n "$(find "$HDFS_NAMENODE_DIR" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
            echo 'Refusing to format a nonempty NameNode directory without VERSION.' >&2
            exit 1
        fi
        exec hdfs namenode -format -nonInteractive
    fi
    if [[ ! -f "$HDFS_NAMENODE_DIR/current/VERSION" ]]; then
        echo 'NameNode is not initialized. Run init-namenode explicitly before starting master.' >&2
        exit 1
    fi
else
    check_directory dfs.datanode.data.dir "$HDFS_DATANODE_DIR"
    mkdir -p "$HDFS_DATANODE_DIR"
    [[ -w "$HDFS_DATANODE_DIR" ]] || { echo 'DataNode directory is not writable by the Hadoop user.' >&2; exit 1; }
fi

first=0
second=0
cleanup() {
    trap - EXIT
    if [[ "$first" != 0 ]]; then kill -TERM "$first" 2>/dev/null || true; fi
    if [[ "$second" != 0 ]]; then kill -TERM "$second" 2>/dev/null || true; fi
    if [[ "$first" != 0 ]]; then wait "$first" 2>/dev/null || true; fi
    if [[ "$second" != 0 ]]; then wait "$second" 2>/dev/null || true; fi
}
trap cleanup EXIT
trap 'exit 143' TERM
trap 'exit 130' INT
if [[ "$role" == master ]]; then
    hdfs namenode & first=$!
    yarn resourcemanager & second=$!
else
    hdfs datanode & first=$!
    yarn nodemanager & second=$!
fi
status=0
wait -n "$first" "$second" || status=$?
echo "A Hadoop service exited (status $status); stopping the peer service." >&2
# Even a service's normal exit is unexpected for a running node.
[[ "$status" -ne 0 ]] || status=1
exit "$status"
