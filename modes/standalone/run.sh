#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
[[ $# -ge 1 && $# -le 2 ]] || { echo 'Usage: run.sh <run-id> [local-input-file-or-directory]' >&2; exit 2; }
m5_id "$1"
input="${2:-$M5_STANDALONE/input}"
m5_collect "$input"
run="$M5_ROOT/runtime/member5/standalone/$1"
[[ ! -e "$run" && ! -L "$run" ]] || { echo "Run/output already exists: $run" >&2; exit 1; }
m5_config file:///
if jps | awk '$2 ~ /^(NameNode|DataNode|ResourceManager|NodeManager)$/ {found=1} END {exit !found}'; then
    echo 'Standalone mode must not run HDFS/YARN daemons.' >&2; exit 1
fi
mkdir -- "$run"
mkdir -- "$run/input"
for file in "${M5_FILES[@]}"; do cp -- "$file" "$run/input/"; done
printf 'Input=%s\nSnapshot=%s\nOutput=%s\n' "$input" "$run/input" "$run/output" | tee "$run/config.log"
m5_counts "file://$run/input" > "$run/expected.tsv"
hadoop jar "$HADOOP_HOME/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar" \
    wordcount "$run/input" "$run/output" 2>&1 | tee "$run/job.log"
bash "$M5_STANDALONE/verify.sh" "$1"
