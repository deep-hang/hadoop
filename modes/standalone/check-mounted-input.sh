#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob
files=(/member5-input/*)
if ((${#files[@]} == 0)); then
  echo 'Docker input mount contains no readable files: /member5-input' >&2
  exit 1
fi
for file in "${files[@]}"; do
  if [[ ! -f "$file" ]] || ! cat -- "$file" >/dev/null; then
    echo "Docker input mount is unreadable: $file" >&2
    exit 1
  fi
done
exec "$@"
