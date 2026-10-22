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

m5_collect() {
    local input="$1" file name
    M5_FILES=()
    if [[ -f "$input" ]]; then
        name="$(basename -- "$input")"
        [[ "$name" != .* && "$name" != _* ]] && M5_FILES+=("$input")
    elif [[ -d "$input" ]]; then
        shopt -s nullglob
        for file in "$input"/*; do
            name="$(basename -- "$file")"
            [[ "$name" != _* ]] || continue
            [[ -f "$file" ]] || { echo 'Nested input directories are not supported.' >&2; return 1; }
            M5_FILES+=("$file")
        done
    fi
    [[ ${#M5_FILES[@]} -gt 0 ]] || { echo "Input file/directory is missing or empty: $input" >&2; return 1; }
}

m5_counts() {
    local input="$1" scratch classpath code=0
    scratch="$(mktemp -d)"
    classpath="$(hadoop classpath --glob)"
    if javac -encoding UTF-8 -cp "$classpath" -d "$scratch" "$M5_STANDALONE/InputCounts.java"; then
        java -Xmx256m -cp "$scratch:$classpath" InputCounts "$input" || code=$?
    else
        code=1
    fi
    rm -f -- "$scratch/InputCounts.class"
    rmdir -- "$scratch"
    return "$code"
}

m5_compare() {
    local actual="$1" expected="$2" scratch code=0
    scratch="$(mktemp -d)"
    LC_ALL=C sort "$expected" > "$scratch/expected"
    LC_ALL=C sort "$actual" > "$scratch/actual"
    diff -u "$scratch/expected" "$scratch/actual" || code=1
    rm -f -- "$scratch/expected" "$scratch/actual"
    rmdir -- "$scratch"
    [[ "$code" -eq 0 ]] || { echo 'RESULT_MISMATCH' >&2; return 1; }
    LC_ALL=C sort "$actual"
    printf 'RESULT_PASS '
    awk -F '\t' '{total+=$2; distinct++} END {printf "distinct_words=%d total_words=%.0f\n", distinct, total}' "$actual"
}
