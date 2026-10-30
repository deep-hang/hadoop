#!/usr/bin/env bash
# 核对：重新生成多文件演示数据集后，文件内容与提交版本一致（生成过程可重复）。
set -uo pipefail
cd /workspace || exit 1

before="$(md5sum tests/mergefile/input-multi/*.txt tests/mergefile/expected/multi-expected.txt | md5sum)"
bash tests/mergefile/make-multi-input.sh >/dev/null
after="$(md5sum tests/mergefile/input-multi/*.txt tests/mergefile/expected/multi-expected.txt | md5sum)"

echo "生成前: $before"
echo "生成后: $after"
if [[ "$before" == "$after" ]]; then
    echo "PASS: 重新生成的结果与提交版本一致"
else
    echo "FAIL: 重新生成的结果与提交版本不一致"
    exit 1
fi

echo
echo "=== 固定小样例的输入与预期的字节内容 ==="
for file_path in apps/mergefile/input/a.txt apps/mergefile/input/b.txt apps/mergefile/input/c.txt apps/mergefile/expected/merged-small.txt; do
    echo "--- $file_path ---"
    cat -A "$file_path"
done
