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
trap 'rm -f -- "$actual"' EXIT
cat -- "${parts[@]}" > "$actual"
m5_compare "$actual"
