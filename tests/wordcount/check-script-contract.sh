#!/usr/bin/env bash
#
# 静态检查 WordCount 三个应用脚本的接口与参数行为。
#
# 不需要 HDFS / YARN / Docker，在电脑或任意 Linux/macOS 的 Bash 里就能跑，
# 用来确认脚本存在、换行为 LF、语法正确、参数个数不对时返回非零。
#
# 用法（项目根目录执行）：
#   bash tests/wordcount/check-script-contract.sh
# 预期：全部 PASS，退出码 0；任一失败退出码 1。
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
APP_DIR="${PROJECT_ROOT}/apps/wordcount"

PASS=0
FAIL=0

ok() {
    PASS=$((PASS + 1))
    echo "  PASS  $1"
}

ng() {
    FAIL=$((FAIL + 1))
    echo "  FAIL  $1"
}

echo "== 1. 脚本存在且可读 =="
for name in build.sh run.sh verify.sh; do
    if [ -f "${APP_DIR}/${name}" ]; then ok "${name} 存在"; else ng "${name} 缺失"; fi
done

echo "== 2. 换行符为 LF（Windows 下混入 CRLF 会让脚本在容器里报错）=="
for name in build.sh run.sh verify.sh; do
    if [ ! -f "${APP_DIR}/${name}" ]; then
        ng "${name} 无法检查（文件缺失）"
        continue
    fi
    if grep -q $'\r' "${APP_DIR}/${name}"; then
        ng "${name} 含 CR 字符"
    else
        ok "${name} 为 LF"
    fi
done

echo "== 3. 语法检查 bash -n =="
for name in build.sh run.sh verify.sh; do
    [ -f "${APP_DIR}/${name}" ] || { ng "${name} 无法检查（文件缺失）"; continue; }
    if bash -n "${APP_DIR}/${name}" 2>/dev/null; then ok "${name} 语法正确"; else ng "${name} 语法错误"; fi
done

# 期望返回非零：参数个数不对时必须失败，避免“少传参数也返回 0”的假成功。
expect_nonzero() {
    local desc="$1"
    shift
    "$@" >/dev/null 2>&1
    local code=$?
    if [ "${code}" -ne 0 ]; then
        ok "${desc}（退出码 ${code}）"
    else
        ng "${desc}（期望非 0，实际 0）"
    fi
}

echo "== 4. 参数个数错误时返回非零 =="
expect_nonzero "run.sh 无参数" bash "${APP_DIR}/run.sh"
expect_nonzero "run.sh 只给 1 个参数" bash "${APP_DIR}/run.sh" /project/input/wordcount
expect_nonzero "run.sh 给 3 个参数" bash "${APP_DIR}/run.sh" a b c
expect_nonzero "verify.sh 无参数" bash "${APP_DIR}/verify.sh"
expect_nonzero "verify.sh 给 2 个参数" bash "${APP_DIR}/verify.sh" a b

echo "== 5. 未编译时 run.sh 明确失败 =="
if [ -f "${APP_DIR}/build/wordcount.jar" ]; then
    echo "  SKIP  已存在 build/wordcount.jar，跳过该检查"
else
    expect_nonzero "run.sh 在未编译时失败" bash "${APP_DIR}/run.sh" /project/input/wordcount /project/output/wordcount/x
fi

echo
echo "结果: PASS=${PASS} FAIL=${FAIL}"
if [ "${FAIL}" -gt 0 ]; then
    echo "SCRIPT CONTRACT FAIL"
    exit 1
fi
echo "SCRIPT CONTRACT PASS"
