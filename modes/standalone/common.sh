#!/usr/bin/env bash
# Member 5 container helpers. No mutation of installed/shared configuration.
set -euo pipefail
M5_STANDALONE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
M5_ROOT="$(cd -- "$M5_STANDALONE/../.." && pwd)"

m5_id() {
    [[ $# -eq 1 && "$1" =~ ^[a-zA-Z0-9_-]+$ ]] || {
        echo 'run-id must contain only letters, digits, underscore or hyphen.' >&2
        return 2
    }
}

m5_config() {
    local expected="$1" scratch classpath code=0
    scratch="$(mktemp -d)"
    classpath="$(hadoop classpath --glob)"
    if javac -encoding UTF-8 -cp "$classpath" -d "$scratch" "$M5_STANDALONE/ModeProbe.java"; then
        java -Xmx128m -cp "$scratch:$classpath" ModeProbe "$expected" || code=$?
    else
        code=1
    fi
    rm -f -- "$scratch/ModeProbe.class"
    rmdir -- "$scratch"
    return "$code"
}

m5_compare() {
    local actual="$1" expected scratch code=0
    scratch="$(mktemp -d)"
    expected="$M5_STANDALONE/expected.tsv"
    LC_ALL=C sort "$expected" > "$scratch/expected"
    LC_ALL=C sort "$actual" > "$scratch/actual"
    diff -u "$scratch/expected" "$scratch/actual" || code=1
    rm -f -- "$scratch/expected" "$scratch/actual"
    rmdir -- "$scratch"
    [[ "$code" -eq 0 ]] || { echo 'RESULT_MISMATCH' >&2; return 1; }
    printf 'RESULT_PASS hadoop=1 hello=2\n'
}
