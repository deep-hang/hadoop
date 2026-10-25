#!/usr/bin/env bash
# Explicit web-only runner: structured events surround real operations.
set -eEuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
[[ $# -eq 4 ]] || exit 2
mode="$1"; id="$2"; source_input="$3"; token="$4"
[[ "$mode" == standalone || "$mode" == pseudo ]] || exit 2
m5_id "$id"
[[ "$token" =~ ^[a-f0-9]{32}$ ]] || exit 2
stage=config
event() {
    printf '__M5_WEB_%s__{"mode":"%s","id":"%s","stage":"%s","status":"%s","time":"%s"}\n' \
      "$token" "$mode" "$id" "$stage" "$1" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
trap 'code=$?; event failed; exit "$code"' ERR
event running
m5_collect "$source_input"
if [[ "$mode" == standalone ]]; then m5_config file:///; else m5_config hdfs://pseudo:9000; fi
event success
stage=services; event running
if [[ "$mode" == standalone ]]; then
    if jps | awk '$2 ~ /^(NameNode|DataNode|ResourceManager|NodeManager)$/ {found=1} END {exit !found}'; then
        echo 'Standalone must not run HDFS/YARN daemons.' >&2; false
    fi
else
    hdfs dfsadmin -report | grep -Fx 'Live datanodes (1):'
    hdfs dfsadmin -safemode get | grep -Fx 'Safe mode is OFF'
    hdfs dfs -ls / >/dev/null
fi
event success
stage=input; event running
if [[ "$mode" == standalone ]]; then
    run="$M5_ROOT/runtime/member5/standalone/$id"
    [[ ! -e "$run" && ! -L "$run" ]] || { echo "Run/output already exists: $run" >&2; false; }
    mkdir -- "$run"; mkdir -- "$run/input"
    for file in "${M5_FILES[@]}"; do cp -- "$file" "$run/input/"; done
    input="$run/input"; output="$run/output"
    printf 'Input=%s\nSnapshot=%s\nOutput=%s\n' "$source_input" "$input" "$output" | tee "$run/config.log"
    m5_counts "file://$input" > "$run/expected.tsv"
else
    input="/project/input/member5/$id"; output="/project/output/member5/$id"
    for path in "$input" "$output"; do
        if hdfs dfs -test -e "$path"; then echo "HDFS input/output already exists: $path" >&2; false; fi
    done
    hdfs dfs -mkdir -p /project/input/member5 /project/output/member5
    hdfs dfs -mkdir "$input"
    for file in "${M5_FILES[@]}"; do hdfs dfs -put "$(m5_file_uri "$file")" "$input/"; done
    hdfs dfs -test -d "$input"
fi
event success
stage=compute; event running
if [[ "$mode" == standalone ]]; then
    hadoop jar "$HADOOP_HOME/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar" wordcount "$input" "$output" 2>&1 | tee "$run/job.log"
else
    hadoop jar "$HADOOP_HOME/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar" wordcount "$input" "$output"
fi
event success
stage=verify; event running
bash "$M5_ROOT/modes/$mode/verify.sh" "$id"
event success
