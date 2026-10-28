#!/usr/bin/env bash
# 运行 MergeFile 作业：bash run.sh <input> <output>
#   input   HDFS 目录（内含多个文本文件）或单个文本文件
#   output  输出目录，必须不存在（脚本不删除用户已有数据）
# 成功后结果文件为 <output>/merged.txt，作业日志中保留 Mapper/Reducer 统计。
set -euo pipefail

MODULE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JAR_FILE="$MODULE_DIR/build/mergefile.jar"
DRIVER_CLASS="com.example.mergefile.MergeFileDriver"
RESULT_FILE="merged.txt"

EXIT_USAGE=2
EXIT_ENV=3
EXIT_NO_INPUT=4
EXIT_OUTPUT_EXISTS=5
EXIT_JOB=6
EXIT_LAYOUT=7

die() {
    local code="$1"
    shift
    echo "[mergefile][run] 错误: $*" >&2
    exit "$code"
}

usage() {
    echo "用法: bash $(basename "$0") <input> <output>" >&2
    echo "  input   HDFS 目录（内含多个文本文件）或单个文本文件" >&2
    echo "  output  输出目录，必须不存在" >&2
}

[[ $# -eq 2 ]] || { usage; exit "$EXIT_USAGE"; }
INPUT="$1"
OUTPUT="$2"
[[ -n "$INPUT" && -n "$OUTPUT" ]] || { usage; exit "$EXIT_USAGE"; }
[[ "$INPUT" != "$OUTPUT" ]] || die "$EXIT_USAGE" "输入与输出路径不能相同: $INPUT"

[[ -f "$JAR_FILE" ]] || die "$EXIT_ENV" "未找到 $JAR_FILE，请先执行 build.sh"
command -v hadoop >/dev/null 2>&1 || die "$EXIT_ENV" "找不到 hadoop 命令"
command -v hdfs >/dev/null 2>&1 || die "$EXIT_ENV" "找不到 hdfs 命令"

ERR_FILE="$(mktemp)"
trap 'rm -f "$ERR_FILE"' EXIT

if ! hdfs dfs -ls "$INPUT" >/dev/null 2>"$ERR_FILE"; then
    if grep -qiE 'no such file|not found|does not exist' "$ERR_FILE"; then
        die "$EXIT_NO_INPUT" "输入路径不存在: $INPUT"
    fi
    die "$EXIT_ENV" "无法访问输入路径 $INPUT，请确认 HDFS 已就绪: $(tr '\n' ' ' <"$ERR_FILE")"
fi

if hdfs dfs -test -e "$OUTPUT" >/dev/null 2>&1; then
    die "$EXIT_OUTPUT_EXISTS" "输出路径已存在: $OUTPUT（不自动删除已有数据，请换一个新输出目录）"
fi

echo "[mergefile][run] 提交作业: input=$INPUT output=$OUTPUT"
if ! hadoop jar "$JAR_FILE" "$DRIVER_CLASS" "$INPUT" "$OUTPUT"; then
    die "$EXIT_JOB" "MapReduce 作业执行失败"
fi

hdfs dfs -test -e "$OUTPUT/_SUCCESS" >/dev/null 2>&1 \
    || die "$EXIT_LAYOUT" "输出目录缺少 _SUCCESS 标记: $OUTPUT"

PART_FILES="$(hdfs dfs -ls "$OUTPUT" 2>/dev/null | awk '{print $NF}' | grep -E '(^|/)part-r-[0-9]+$' || true)"
PART_COUNT="$(printf '%s\n' "$PART_FILES" | grep -c 'part-r-' || true)"
[[ "$PART_COUNT" -eq 1 ]] || die "$EXIT_LAYOUT" "期望 1 个结果文件，实际 $PART_COUNT 个: $PART_FILES"

hdfs dfs -mv "$PART_FILES" "$OUTPUT/$RESULT_FILE" >/dev/null \
    || die "$EXIT_LAYOUT" "把 $PART_FILES 重命名为 $RESULT_FILE 失败"

echo "[mergefile][run] 输出目录内容:"
hdfs dfs -ls "$OUTPUT"
echo "[mergefile][run] 结果文件: $OUTPUT/$RESULT_FILE"
echo "[mergefile][run] 查看内容: hdfs dfs -cat '$OUTPUT/$RESULT_FILE'"