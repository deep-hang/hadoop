#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/../standalone/common.sh"
[[ $# -eq 1 ]] || { echo 'Usage: run.sh <run-id>' >&2; exit 2; }
m5_id "$1"
m5_config hdfs://pseudo:9000
bash "$M5_ROOT/modes/pseudo/healthcheck.sh"
input="/project/input/member5/$1"
output="/project/output/member5/$1"
for path in "$input" "$output"; do
    if hdfs dfs -test -e "$path"; then echo "HDFS input/output already exists: $path" >&2; exit 1; fi
done
hdfs dfs -mkdir -p /project/input/member5 /project/output/member5
hdfs dfs -mkdir "$input"
hdfs dfs -put "$M5_STANDALONE/input/sample.txt" "$input/sample.txt"
hadoop jar "$HADOOP_HOME/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar" \
    wordcount "$input" "$output"
bash "$M5_ROOT/modes/pseudo/verify.sh" "$1"
