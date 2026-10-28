#!/usr/bin/env bash
# 核对本模块提交的文件：换行符必须是 LF，不能带 UTF-8 BOM，脚本要有可执行意图。
set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGETS=(
    "apps/mergefile/build.sh"
    "apps/mergefile/run.sh"
    "apps/mergefile/verify.sh"
    "tests/mergefile/run-tests.sh"
    "tests/mergefile/verify-multi.sh"
    "tests/mergefile/make-multi-input.sh"
    "tests/mergefile/run-cluster-demo.sh"
    "tests/mergefile/run-cluster-tests.sh"
    "tests/mergefile/collect-evidence.sh"
    "tests/mergefile/collect-node-evidence.sh"
    "tests/mergefile/check-example-jar.sh"
    "tests/mergefile/check-scripts.sh"
    "tests/mergefile/check-fixtures.sh"
)

problems=0
for relative_path in "${TARGETS[@]}"; do
    file_path="$REPO_DIR/$relative_path"
    if [[ ! -f "$file_path" ]]; then
        echo "缺少文件: $relative_path"
        problems=$((problems + 1))
        continue
    fi
    if head -c 3 "$file_path" | od -An -tx1 | grep -qi 'ef bb bf'; then
        echo "文件带 BOM: $relative_path"
        problems=$((problems + 1))
    fi
    if grep -qU $'\r' "$file_path"; then
        echo "文件含 CRLF: $relative_path"
        problems=$((problems + 1))
    fi
    if [[ "$(head -1 "$file_path")" != "#!/usr/bin/env bash" ]]; then
        echo "缺少 bash shebang: $relative_path"
        problems=$((problems + 1))
    fi
done

if [[ "$problems" -gt 0 ]]; then
    echo "发现 $problems 个问题"
    exit 1
fi
echo "换行符与 shebang 检查通过（${#TARGETS[@]} 个脚本）"
