#!/usr/bin/env bash
# 在 master 容器内以 HDFS 模式运行 MergeFile 模块的全部测试用例。
#
# 用法（在集群的 master 容器内执行）：
#   bash /workspace/tests/mergefile/run-cluster-tests.sh
#
# 公共验证配置把仓库挂成只读，build.sh 需要可写的 build/ 目录，
# 所以先把 apps/ 与 tests/ 复制到临时目录再跑。
set -uo pipefail

WORK_ROOT=/tmp/mergefile-cluster-tests

rm -rf "$WORK_ROOT"
mkdir -p "$WORK_ROOT"
cp -r /workspace/apps "$WORK_ROOT/apps"
cp -r /workspace/tests "$WORK_ROOT/tests"
rm -rf "$WORK_ROOT/apps/mergefile/build"

cd "$WORK_ROOT"
bash tests/mergefile/run-tests.sh --hdfs
exit $?
