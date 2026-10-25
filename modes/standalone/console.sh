#!/usr/bin/env bash
set -euo pipefail
python_bin=python3
case "$(command -v python3 || true)" in ''|*WindowsApps*) python_bin=python ;; esac
entry="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/console.py"
arguments=("$@")
if command -v cygpath >/dev/null; then
    entry="$(cygpath -w "$entry")"
    for ((i=0; i<${#arguments[@]}; i++)); do
        if [[ "${arguments[i]}" == --input && $((i+1)) -lt ${#arguments[@]} ]]; then
            arguments[i+1]="$(cygpath -w "${arguments[i+1]}")"
        fi
    done
fi
exec "$python_bin" -B "$entry" "${arguments[@]}"
