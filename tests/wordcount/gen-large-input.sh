#!/usr/bin/env bash
#
# 生成“多文件、较大规模”的演示输入，并同时算出该数据集的预期词频。
#
# 为什么需要它：
#   apps/wordcount/input/ 里的固定小样例只有 3 个词，验证功能足够，但演示“两个 Worker
#   都参与计算”太少。这里生成多份文件、每份多行，Map 任务数会随分片数增加，便于在
#   YARN UI 上看到任务落到不同节点。
#
# 为什么不提交生成结果：
#   生成物写在 tests/wordcount/build/ 下，该目录被 .gitignore 的 **/build/ 规则忽略，
#   数据可由脚本复现，不往仓库塞大文件。
#
# 预期词频怎么算的：
#   用 tr / sort / uniq 这套 shell 工具独立数一遍，和 Java 逻辑是两套实现；
#   两边结果一致才算真正对上，避免“自己验证自己”。
#   数据全部为 ASCII 单词，因此这里用 POSIX 字符类即可，与 Java 的 \p{L}\p{N} 等价。
#
# 用法（项目根目录执行）：
#   bash tests/wordcount/gen-large-input.sh [文件数] [每个文件行数]
#   默认 5 个文件 × 2000 行。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${SCRIPT_DIR}/build/large"
EXPECTED_DIR="${SCRIPT_DIR}/build/expected"

FILE_COUNT="${1:-5}"
LINES_PER_FILE="${2:-2000}"

case "${FILE_COUNT}" in
    ''|*[!0-9]*) echo "文件数必须是整数：${FILE_COUNT}" >&2; exit 2 ;;
esac
case "${LINES_PER_FILE}" in
    ''|*[!0-9]*) echo "行数必须是整数：${LINES_PER_FILE}" >&2; exit 2 ;;
esac
[ "${FILE_COUNT}" -ge 1 ] || { echo "文件数至少为 1" >&2; exit 2; }
[ "${LINES_PER_FILE}" -ge 1 ] || { echo "行数至少为 1" >&2; exit 2; }

# 词表故意多选几个，让不同单词的次数分散，对比结果时更容易看出错在哪。
WORDS=(hadoop mapreduce hdfs yarn namenode datanode resourcemanager nodemanager shuffle reducer inputformat)

rm -rf "${OUT_DIR}"
mkdir -p "${OUT_DIR}" "${EXPECTED_DIR}"

echo "生成 ${FILE_COUNT} 个文件，每个 ${LINES_PER_FILE} 行 -> ${OUT_DIR}"
for ((f = 1; f <= FILE_COUNT; f++)); do
    target="${OUT_DIR}/part-$(printf '%02d' "${f}").txt"
    : > "${target}"
    for ((l = 1; l <= LINES_PER_FILE; l++)); do
        line=""
        for k in 1 2 3 4; do
            index=$(((f * 7 + l * 3 + k * 5) % ${#WORDS[@]}))
            line+="${WORDS[${index}]} "
        done
        # 每 17 行掺入大写和标点，覆盖分词规则里的“忽略大小写、标点作分隔符”。
        if [ $((l % 17)) -eq 0 ]; then
            line+="HADOOP, Yarn. \"quoted\""
        fi
        printf '%s\n' "${line}" >> "${target}"
    done
done

EXPECTED_FILE="${EXPECTED_DIR}/large.tsv"
echo "独立统计预期词频 -> ${EXPECTED_FILE}"
cat "${OUT_DIR}"/*.txt \
    | LC_ALL=C tr -cs '[:alnum:]' '\n' \
    | LC_ALL=C tr 'A-Z' 'a-z' \
    | sed '/^$/d' \
    | LC_ALL=C sort \
    | LC_ALL=C uniq -c \
    | awk '{printf "%s\t%s\n", $2, $1}' \
    | LC_ALL=C sort -k1,1 > "${EXPECTED_FILE}"

WORD_LINES="$(wc -l < "${EXPECTED_FILE}" | tr -d ' ')"
TOTAL_HITS="$(awk -F'\t' '{s += $2} END {print s}' "${EXPECTED_FILE}")"

echo "GEN PASS: ${FILE_COUNT} 个输入文件，不同单词 ${WORD_LINES} 个，单词总出现次数 ${TOTAL_HITS}"
echo "  输入目录: ${OUT_DIR}"
echo "  预期文件: ${EXPECTED_FILE}"
