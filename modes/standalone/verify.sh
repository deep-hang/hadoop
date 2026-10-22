#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
[[ $# -eq 1 ]] || { echo 'Usage: verify.sh <run-id>' >&2; exit 2; }
m5_id "$1"
output="$M5_ROOT/runtime/member5/standalone/$1/output"
[[ -f "$output/_SUCCESS" ]] || { echo "Missing success marker: $output" >&2; exit 1; }
shopt -s nullglob
parts=("$output"/part-r-*)
[[ ${#parts[@]} -gt 0 ]] || { echo 'No result parts.' >&2; exit 1; }
actual="$(mktemp)"
expected="$(mktemp)"
trap 'rm -f -- "$actual" "$expected"' EXIT
cat -- "${parts[@]}" > "$actual"
run="${output%/output}"
if [[ -d "$run/input" ]]; then
    m5_counts "file://$run/input" > "$expected"
elif [[ -f "$run/config.log" ]] && grep -Fx "Input=$M5_STANDALONE/input" "$run/config.log" >/dev/null; then
    # Compatibility with fixed-sample runs produced before input snapshots existed.
    cp -- "$M5_STANDALONE/expected.tsv" "$expected"
else
    echo 'Missing saved input snapshot.' >&2; exit 1
fi
m5_compare "$actual" "$expected"
