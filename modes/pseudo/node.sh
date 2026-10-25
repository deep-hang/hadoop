#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 1 && "$1" =~ ^(init|start)$ ]] || { echo 'Usage: node.sh {init|start}' >&2; exit 2; }
[[ "$(id -u)" == 1000 ]] || { echo 'Run as image user hadoop (UID 1000).' >&2; exit 1; }
nn=/var/lib/hadoop/hdfs/namenode
dn=/var/lib/hadoop/hdfs/datanode
[[ "$(hdfs getconf -confKey fs.defaultFS)" == hdfs://pseudo:9000 ]]
[[ "$(hdfs getconf -confKey dfs.namenode.name.dir)" == "$nn" ]]
[[ "$(hdfs getconf -confKey dfs.datanode.data.dir)" == "$dn" ]]
[[ -w /var/lib/hadoop ]] || { echo 'Persistent volume is not writable by UID 1000.' >&2; exit 1; }
# The descriptor lock lives for the entire service lifetime, including across containers.
exec 9>/var/lib/hadoop/.member5.lock
flock -n 9 || { echo 'Pseudo services or initialization already running; refusing concurrent init/start.' >&2; exit 1; }
mkdir -p -- "$nn" "$dn"
[[ -w "$nn" && -w "$dn" ]] || { echo 'HDFS directories are not writable.' >&2; exit 1; }
if [[ "$1" == init ]]; then
    if [[ -f "$nn/current/VERSION" ]]; then
        echo 'Already initialized; preserving metadata and data.'; exit 0
    fi
    for directory in "$nn" "$dn"; do
        if [[ -n "$(find "$directory" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
            echo "Refusing to format nonempty HDFS directory without NameNode VERSION: $directory" >&2
            exit 1
        fi
    done
    hdfs namenode -format -nonInteractive
    exit $?
fi
[[ -f "$nn/current/VERSION" ]] || { echo 'NameNode not initialized. Run init explicitly.' >&2; exit 1; }
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
hdfs namenode & first=$!
hdfs datanode & second=$!
status=0
wait -n "$first" "$second" || status=$?
echo "A pseudo service exited ($status); stopping its peer." >&2
[[ "$status" -ne 0 ]] || status=1
exit "$status"
