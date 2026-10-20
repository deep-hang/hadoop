#!/usr/bin/env bash
# Host-side behavior tests. Git Bash works; no Java/Hadoop/Docker required.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
scratch="$(mktemp -d)"
trap 'rm -rf -- "$scratch"' EXIT
export JAVA_HOME="$scratch/java"
export HADOOP_HOME="$scratch/hadoop"
export HADOOP_CONF_DIR="$scratch/conf"
expect_exit() {
    local expected="$1" actual=0
    shift
    "$@" > "$scratch/output" 2>&1 || actual=$?
    if [[ "$actual" != "$expected" ]]; then
        cat "$scratch/output" >&2
        echo "Expected exit $expected; got $actual" >&2
        exit 1
    fi
}
expect_exit 1 bash docker/entrypoint.sh true
grep -F 'Missing Java or Hadoop' "$scratch/output"
mkdir -p "$JAVA_HOME/bin" "$HADOOP_HOME/bin"
printf '#!/usr/bin/env bash\nexit 0\n' > "$JAVA_HOME/bin/java"
printf '#!/usr/bin/env bash\nexit 0\n' > "$HADOOP_HOME/bin/hadoop"
chmod +x "$JAVA_HOME/bin/java" "$HADOOP_HOME/bin/hadoop"
expect_exit 1 bash docker/entrypoint.sh true
grep -F 'Missing configuration directory' "$scratch/output"
mkdir -p "$HADOOP_CONF_DIR"
expect_exit 7 bash docker/entrypoint.sh bash -c 'exit 7'
expect_exit 0 bash docker/entrypoint.sh bash -c '[[ "$1" == "argument with spaces" ]]' _ 'argument with spaces'
printf 'PASS: missing tools, missing configuration, exit propagation, argument boundaries\n'
