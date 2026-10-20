#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
action="${1:-doctor}"
case "$action" in doctor|config|build|verify|shell) ;; *) echo 'Usage: bash scripts/dev.sh {doctor|config|build|verify|shell}' >&2; exit 2;; esac
command -v docker >/dev/null || { echo 'Docker is missing; see docs/windows-setup.md.' >&2; exit 1; }
docker compose version
compose=(docker compose --env-file .development -f compose/bootstrap.yaml)
if [[ "$action" == config ]]; then
    "${compose[@]}" config --quiet
    exit
fi
container_os="$(docker info --format '{{.OSType}}')"
[[ "$container_os" == linux ]] || { echo 'Switch Docker to Linux containers.' >&2; exit 1; }
case "$action" in
    doctor) "${compose[@]}" config --quiet ;;
    build) "${compose[@]}" build ;;
    verify) "${compose[@]}" run --rm -T dev bash tests/verify-base.sh ;;
    shell) "${compose[@]}" run --rm dev bash ;;
esac
