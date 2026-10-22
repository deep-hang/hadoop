#!/usr/bin/env bash
set -euo pipefail
mode="${1:-}"
action="${2:-doctor}"
id="${3:-}"
[[ $# -le 3 && "$mode" =~ ^(standalone|pseudo)$ ]] || { echo 'Invalid arguments.' >&2; exit 2; }
case "$action" in
    doctor|shell|test) [[ -z "$id" ]] || exit 2 ;;
    run|verify) [[ "$id" =~ ^[a-zA-Z0-9_-]+$ ]] || { echo 'Invalid or missing run-id.' >&2; exit 2; } ;;
    init|up|status|logs|restart|stop|down) [[ "$mode" == pseudo && -z "$id" ]] || exit 2 ;;
    *) echo 'Unknown action.' >&2; exit 2 ;;
esac
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
mkdir -p "$root/runtime/member5/standalone" "$root/runtime/member5/$mode/control"
log="$root/runtime/member5/$mode/control/$(date -u +%Y%m%dT%H%M%S)-$$-$RANDOM.log"
if [[ "$action" == test ]]; then
    if command -v python3 >/dev/null; then python3 "$root/tests/$mode/check-$mode.py"
    else python "$root/tests/$mode/check-$mode.py"; fi
    exit $?
fi
cli_root="$root"
if command -v cygpath >/dev/null; then cli_root="$(cygpath -w "$root")"; fi
export MSYS_NO_PATHCONV=1
project="hadoop-m5-$mode"
compose=(docker compose --env-file "$cli_root/.development" -f "$cli_root/modes/$mode/compose.yaml" -p "$project")
dc() { "${compose[@]}" "$@" 2>&1 | tee -a "$log"; }
wait_pseudo() {
    if dc up -d --no-build --wait --wait-timeout 180 pseudo; then return 0; fi
    dc ps -a || true
    dc logs --no-color --tail 100 pseudo || true
    return 1
}
[[ "$(docker info --format '{{.OSType}}')" == linux ]] || { echo 'Start Docker with Linux containers.' >&2; exit 1; }
dc config --quiet
case "$action" in
    doctor)
        docker compose version | tee -a "$log"
        docker image inspect hadoop-base:v0.1 --format '{{.Id}}' | tee -a "$log"
        echo "DOCTOR_PASS mode=$mode project=$project" ;;
    run|verify)
        if [[ "$mode" == standalone ]]; then dc run --rm -T --no-deps standalone bash "/workspace/modes/standalone/$action.sh" "$id"
        else dc exec -T pseudo bash "/workspace/modes/pseudo/$action.sh" "$id"; fi ;;
    shell)
        if [[ "$mode" == standalone ]]; then "${compose[@]}" run --rm standalone bash
        else "${compose[@]}" exec pseudo bash; fi ;;
    init)
        running="$(docker ps --filter "label=com.docker.compose.project=$project" --format '{{.ID}}')"
        [[ -z "$running" ]] || { echo 'Pseudo services or initialization already running; stop before init.' >&2; exit 1; }
        dc run --rm -T --no-deps pseudo bash /workspace/modes/pseudo/node.sh init ;;
    up) wait_pseudo ;;
    restart) dc restart pseudo; wait_pseudo ;;
    status) dc ps -a; dc exec -T pseudo bash /workspace/modes/pseudo/healthcheck.sh; dc exec -T pseudo jps ;;
    logs) dc logs --no-color --tail 200 pseudo ;;
    stop) dc stop pseudo ;;
    down) dc down ;;
esac
echo "Evidence: $log"
