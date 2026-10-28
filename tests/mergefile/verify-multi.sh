#!/usr/bin/env bash
# 核对多文件演示数据集的合并结果：bash verify-multi.sh <output>
#
# 与 apps/mergefile/verify.sh 的区别：
#   verify.sh      核对"固定小样例"（apps/mergefile/expected/merged-small.txt），是公共接口的一部分
#   verify-multi.sh 核对"多文件演示数据集"（tests/mergefile/expected/multi-expected.txt），
#                   只用于双 Worker 演示，不能替代 verify.sh
#
# 路径按 HDFS 解释，本地调试时可传 file:// 开头的路径。
# 全部通过返回 0，任何一项不通过返回非零。
set -uo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPECTED_FILE="$TEST_DIR/expected/multi-expected.txt"
RESULT_FILE="merged.txt"

EXIT_USAGE=2
EXIT_ENV=3
EXIT_MISSING=4
EXIT_CONTENT=5

die() {
    local code="$1"
    shift
    echo "[mergefile][verify-multi] 错误: $*" >&2
    exit "$code"
}

usage() {
    echo "用法: bash $(basename "$0") <output>" >&2
    echo "  output  run.sh 生成的输出目录" >&2
}

[[ $# -eq 1 ]] || { usage; exit "$EXIT_USAGE"; }
OUTPUT="$1"
[[ -n "$OUTPUT" ]] || { usage; exit "$EXIT_USAGE"; }

[[ -f "$EXPECTED_FILE" ]] || die "$EXIT_ENV" "缺少预期结果文件: $EXPECTED_FILE"
command -v hdfs >/dev/null 2>&1 || die "$EXIT_ENV" "找不到 hdfs 命令"

ERR_FILE="$(mktemp)"
ACTUAL_FILE="$(mktemp)"
trap 'rm -f "$ERR_FILE" "$ACTUAL_FILE"' EXIT

# 1. 输出目录必须存在
if ! hdfs dfs -ls "$OUTPUT" >/dev/null 2>"$ERR_FILE"; then
    if grep -qiE 'no such file|not found|does not exist' "$ERR_FILE"; then
        die "$EXIT_MISSING" "输出目录不存在: $OUTPUT"
    fi
    die "$EXIT_ENV" "无法访问输出目录 $OUTPUT，请确认 HDFS 已就绪: $(tr '\n' ' ' <"$ERR_FILE")"
fi

# 2. 必须有 _SUCCESS 和唯一结果文件，且没有未重命名的 part 文件
hdfs dfs -test -e "$OUTPUT/_SUCCESS" >/dev/null 2>&1 \
    || die "$EXIT_MISSING" "输出目录缺少 _SUCCESS 标记: $OUTPUT"
hdfs dfs -test -e "$OUTPUT/$RESULT_FILE" >/dev/null 2>&1 \
    || die "$EXIT_MISSING" "输出目录缺少结果文件 $RESULT_FILE: $OUTPUT"

STRAY_PARTS="$(hdfs dfs -ls "$OUTPUT" 2>/dev/null | awk '{print $NF}' | grep -E '(^|/)part-r-[0-9]+$' || true)"
[[ -z "$STRAY_PARTS" ]] \
    || die "$EXIT_CONTENT" "输出目录仍有未重命名的 part 文件: $STRAY_PARTS"

# 3. 逐行内容与固定预期完全一致（顺序敏感）
hdfs dfs -cat "$OUTPUT/$RESULT_FILE" >"$ACTUAL_FILE"
if ! diff -u "$EXPECTED_FILE" "$ACTUAL_FILE"; then
    die "$EXIT_CONTENT" "输出内容与多文件演示数据集的固定预期不一致（上方为 diff）: $OUTPUT/$RESULT_FILE"
fi

# 4. 每行必须是 3 个制表符分隔的字段：记录、次数、来源文件列表
if ! awk -F'\t' 'NF != 3 { printf "第 %d 行字段数不是 3: %s\n", NR, $0 > "/dev/stderr"; bad = 1 } END { exit bad ? 1 : 0 }' "$ACTUAL_FILE"; then
    die "$EXIT_CONTENT" "输出行格式不符合 记录<TAB>次数<TAB>来源文件列表"
fi

# 5. 记录去重：同一个记录只能出现一次
DUPLICATED="$(awk -F'\t' 'seen[$1]++ > 0 { n++ } END { print n + 0 }' "$ACTUAL_FILE")"
[[ "$DUPLICATED" -eq 0 ]] || die "$EXIT_CONTENT" "输出中存在重复记录 $DUPLICATED 条，违反去重规则"

# 6. 排序：记录按 UTF-8 字节序升序
if ! LC_ALL=C sort -c -t$'\t' -k1,1 "$ACTUAL_FILE"; then
    die "$EXIT_CONTENT" "输出没有按记录的 UTF-8 字节序升序排列"
fi

# 7. 统计信息，便于在实验记录里引用
read_stats() {
    awk -F'\t' '
        { lines++
          if (!($1 in seen)) { seen[$1] = 1; unique++ }
          occurrences += $2
          if ($2 + 0 > max) { max = $2 + 0 }
          if ($2 + 0 > 1) {
            repeated++
            n = split($3, sources, ",")
            if (n >= 2) { cross_file++ }
          }
        }
        END { printf "%d %d %d %d %d %d\n", lines, unique, occurrences, max + 0, repeated + 0, cross_file + 0 }
    ' "$1"
}

read -r exp_lines exp_unique exp_occurrences exp_max exp_repeated exp_cross <<<"$(read_stats "$EXPECTED_FILE")"
read -r act_lines act_unique act_occurrences act_max act_repeated act_cross <<<"$(read_stats "$ACTUAL_FILE")"

[[ "$act_lines" -eq "$exp_lines" ]] || die "$EXIT_CONTENT" "记录行数不符: 实际 $act_lines，预期 $exp_lines"
[[ "$act_unique" -eq "$exp_unique" ]] || die "$EXIT_CONTENT" "唯一记录数不符: 实际 $act_unique，预期 $exp_unique"
[[ "$act_occurrences" -eq "$exp_occurrences" ]] \
    || die "$EXIT_CONTENT" "出现次数合计不符: 实际 $act_occurrences，预期 $exp_occurrences"
[[ "$act_max" -eq "$exp_max" ]] || die "$EXIT_CONTENT" "单条记录最大次数不符: 实际 $act_max，预期 $exp_max"
[[ "$act_repeated" -eq "$exp_repeated" ]] || die "$EXIT_CONTENT" "重复记录条数不符: 实际 $act_repeated，预期 $exp_repeated"
[[ "$act_cross" -eq "$exp_cross" ]] || die "$EXIT_CONTENT" "跨文件重复记录条数不符: 实际 $act_cross，预期 $exp_cross"
[[ "$act_cross" -gt 0 ]] || die "$EXIT_CONTENT" "没有跨文件重复记录，无法证明多文件合并生效"

echo "[mergefile][verify-multi] 记录行数: $act_lines"
echo "[mergefile][verify-multi] 唯一记录数: $act_unique"
echo "[mergefile][verify-multi] 出现次数合计: $act_occurrences"
echo "[mergefile][verify-multi] 单条记录最大次数: $act_max"
echo "[mergefile][verify-multi] 重复记录条数: $act_repeated（其中跨文件重复 $act_cross 条）"
echo "[mergefile][verify-multi] 结果: 通过"
exit 0
