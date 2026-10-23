#!/usr/bin/env bash
set -euo pipefail
scratch="$(mktemp -d)"
trap 'rm -f -- "$scratch"/*.class; rmdir -- "$scratch"' EXIT
classpath="$(hadoop classpath --glob)"
javac -encoding UTF-8 -cp "$classpath" -d "$scratch" \
 /workspace/modes/standalone/ConsoleInspect.java /workspace/modes/standalone/InputCounts.java /workspace/modes/standalone/WebPlusInspect.java
java -Xmx256m -cp "$scratch:$classpath" WebPlusInspect "$@"
