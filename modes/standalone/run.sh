#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
[[ $# -ge 1 && $# -le 2 ]] || { echo 'Usage: run.sh <run-id> [local-input-directory]' >&2; exit 2; }
m5_id "$1"
input="${2:-$M5_STANDALONE/input}"
[[ -d "$input" && -n "$(find "$input" -maxdepth 1 -type f -print -quit)" ]] || {
    echo "Input directory is missing or empty: $input" >&2; exit 1;
}
run="$M5_ROOT/runtime/member5/standalone/$1"
[[ ! -e "$run" && ! -L "$run" ]] || { echo "Run/output already exists: $run" >&2; exit 1; }
m5_config file:///
if jps | awk '$2 ~ /^(NameNode|DataNode|ResourceManager|NodeManager)$/ {found=1} END {exit !found}'; then
    echo 'Standalone mode must not run HDFS/YARN daemons.' >&2; exit 1
fi
mkdir -- "$run"
printf 'Input=%s\nOutput=%s\n' "$input" "$run/output" | tee "$run/config.log"
hadoop jar "$HADOOP_HOME/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar" \
    wordcount "$input" "$run/output" 2>&1 | tee "$run/job.log"
bash "$M5_STANDALONE/verify.sh" "$1"
