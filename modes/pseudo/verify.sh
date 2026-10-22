#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/../standalone/common.sh"
[[ $# -eq 1 ]] || { echo 'Usage: verify.sh <run-id>' >&2; exit 2; }
m5_id "$1"
output="/project/output/member5/$1"
hdfs dfs -test -e "$output/_SUCCESS" || { echo 'Missing HDFS success marker.' >&2; exit 1; }
actual="$(mktemp)"
trap 'rm -f -- "$actual"' EXIT
hdfs dfs -cat "$output/part-r-*" > "$actual"
m5_compare "$actual"
