#!/usr/bin/env bash
# run-all.sh —— 依次执行 HDFS 主链路检查：配置 → DataNode 注册 → 读写 → 块与副本。
# 执行位置：master 容器内。任一项失败即返回非零退出码。
# 重启持久化要跨重启，不在本脚本内：见 check-persistence.sh 的 record / verify 两步。
# 用法：bash /workspace/tests/hdfs/run-all.sh

set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/common.sh"

# common.sh 打开了 set -e；这里要收集全部失败项而不是遇到第一个就退出
set +e

checks=(check-config.sh check-datanodes.sh check-readwrite.sh check-blocks.sh)
failed=()

for check in "${checks[@]}"; do
    info "===== $check ====="
    if ! bash "$HDFS_TEST_DIR/$check"; then
        failed+=("$check")
        info "$check 失败，继续执行后续检查以收集全部问题"
    fi
done

if ((${#failed[@]} > 0)); then
    printf '[hdfs] FAIL: %d 项未通过：%s\n' "${#failed[@]}" "${failed[*]}" >&2
    printf 'HDFS_TEST_FAIL\n' >&2
    exit 1
fi

printf 'HDFS_TEST_PASS\n'
