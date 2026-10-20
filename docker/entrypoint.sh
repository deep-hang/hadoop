#!/usr/bin/env bash
set -euo pipefail

if [[ ! -x "${JAVA_HOME}/bin/java" || ! -x "${HADOOP_HOME}/bin/hadoop" ]]; then
    echo 'Missing Java or Hadoop; rebuild the frozen base image.' >&2
    exit 1
fi
if [[ ! -d "${HADOOP_CONF_DIR}" ]]; then
    echo "Missing configuration directory: ${HADOOP_CONF_DIR}" >&2
    exit 1
fi
# No formatting, daemon startup or implicit configuration changes.
# exec preserves exit codes and forwards signals to the requested process.
exec "$@"
