#!/usr/bin/env bash
# 生成多文件演示数据集与它的固定预期。
#
# 用法：
#   bash tests/mergefile/make-multi-input.sh                       # 默认：8 个小文件，写入 input-multi/
#   bash tests/mergefile/make-multi-input.sh <输入目录> <文件数> <每文件独有记录数> <预期文件>
#
# 目的：为"两个 worker 都有数据与计算参与"的演示准备多文件输入。
# 规则与 apps/mergefile/README.md 一致：
#   - 每个文件都包含全部共享记录 alpha/beta/gamma（跨文件重复）
#   - 每个文件还包含若干条只属于自己的记录 partNN（文件内重复）
#   - 每个文件末尾有一行空行和一行只含空格的行（空行边界）
# 生成结果确定，可重复执行覆盖同一目录。
set -euo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TARGET_DIR="${1:-$TEST_DIR/input-multi}"
FILE_COUNT="${2:-8}"
RECORDS_PER_FILE="${3:-2}"
EXPECTED_FILE="${4:-$TEST_DIR/expected/multi-expected.txt}"

[[ "$FILE_COUNT" -ge 1 ]] || { echo "文件数至少为 1" >&2; exit 2; }
[[ "$RECORDS_PER_FILE" -ge 1 ]] || { echo "每个文件的独有记录数至少为 1" >&2; exit 2; }

# 共享记录名：alpha / beta / gamma，出现在每个输入文件里
SHARED_RECORDS=(alpha beta gamma)

mkdir -p "$TARGET_DIR"
mkdir -p "$(dirname "$EXPECTED_FILE")"

# 生成输入文件
for ((index = 1; index <= FILE_COUNT; index++)); do
    file_name="$(printf 'log-%02d.txt' "$index")"
    {
        for record in "${SHARED_RECORDS[@]}"; do
            printf '%s\n' "$record"
        done
        for ((repeat = 1; repeat <= RECORDS_PER_FILE; repeat++)); do
            printf 'part%02d\n' "$index"
        done
        # 边界：一行空行 + 一行只含空格的行，都应被丢弃
        printf '\n'
        printf '   \n'
    } >"$TARGET_DIR/$file_name"
done

# 生成固定预期：记录按 UTF-8 字节序升序；次数是该记录出现的总次数；
# 来源文件列表按字典序排列并去重。
{
    for record in "${SHARED_RECORDS[@]}"; do
        sources=""
        for ((index = 1; index <= FILE_COUNT; index++)); do
            file_name="$(printf 'log-%02d.txt' "$index")"
            if [[ -z "$sources" ]]; then
                sources="$file_name"
            else
                sources="$sources,$file_name"
            fi
        done
        printf '%s\t%d\t%s\n' "$record" "$FILE_COUNT" "$sources"
    done
    for ((index = 1; index <= FILE_COUNT; index++)); do
        printf 'part%02d\t%d\tlog-%02d.txt\n' "$index" "$RECORDS_PER_FILE" "$index"
    done
} >"$EXPECTED_FILE"

echo "已生成 $FILE_COUNT 个输入文件: $TARGET_DIR"
echo "固定预期: $EXPECTED_FILE"
