#!/usr/bin/env bash
set -euo pipefail
scratch="$(mktemp -d)"
trap 'rm -f -- "$scratch/ConsoleInspect.class"; rmdir -- "$scratch"' EXIT
classpath="$(hadoop classpath --glob)"
javac -encoding UTF-8 -cp "$classpath" -d "$scratch" /workspace/modes/standalone/ConsoleInspect.java
java -Xmx256m -cp "$scratch:$classpath" ConsoleInspect "$@"
