#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
processes="$(jps)"
grep -Eq '^[0-9]+ NameNode$' <<< "$processes"
grep -Eq '^[0-9]+ DataNode$' <<< "$processes"
hdfs dfsadmin -report | grep -Fx 'Live datanodes (1):'
hdfs dfsadmin -safemode get | grep -Fx 'Safe mode is OFF'
hdfs dfs -ls / >/dev/null
echo 'PSEUDO_READY: NameNode, DataNode, one live node, safe mode OFF, HDFS accessible'
