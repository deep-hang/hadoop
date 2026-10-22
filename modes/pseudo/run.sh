#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/../standalone/common.sh"
[[ $# -ge 1 && $# -le 2 ]] || { echo 'Usage: run.sh <run-id> [local-input-file-or-directory]' >&2; exit 2; }
m5_id "$1"
m5_collect "${2:-$M5_STANDALONE/input}"
m5_config hdfs://pseudo:9000
hdfs dfsadmin -report | grep -Fx 'Live datanodes (1):'
hdfs dfsadmin -safemode get | grep -Fx 'Safe mode is OFF'
input="/project/input/member5/$1"
output="/project/output/member5/$1"
for path in "$input" "$output"; do
    if hdfs dfs -test -e "$path"; then echo "HDFS input/output already exists: $path" >&2; exit 1; fi
done
expected="$(mktemp)"
trap 'rm -f -- "$expected"' EXIT
m5_counts "file://${2:-$M5_STANDALONE/input}" > "$expected"
hdfs dfs -mkdir -p /project/input/member5 /project/output/member5
hdfs dfs -mkdir "$input"
source_input="${2:-$M5_STANDALONE/input}"
if [[ -d "$source_input" ]]; then
    # Let Hadoop expand filenames itself: raw CLI paths containing spaces can
    # be reinterpreted as globs. This pattern also excludes hidden entries.
    hdfs dfs -put "$source_input/[^._]*" "$input/"
else
    hdfs dfs -put "$source_input" "$input/member5-input"
fi
hadoop jar "$HADOOP_HOME/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar" \
    wordcount "$input" "$output"
bash "$M5_ROOT/modes/pseudo/verify.sh" "$1"
