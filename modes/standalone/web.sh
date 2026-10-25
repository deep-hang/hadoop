#!/usr/bin/env bash
set -euo pipefail
python_bin=python3
case "$(command -v python3 || true)" in ''|*WindowsApps*) python_bin=python ;; esac
entry="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/web.py"
if command -v cygpath >/dev/null; then entry="$(cygpath -w "$entry")"; fi
exec "$python_bin" -B "$entry" "$@"
