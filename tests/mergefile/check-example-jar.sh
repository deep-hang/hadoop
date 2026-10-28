#!/usr/bin/env bash
# 核对参考来源：Hadoop 3.3.6 自带的 examples JAR 里有没有 MergeFile 示例。
#
# 用法（在公共开发容器内执行）：
#   bash /workspace/tests/mergefile/check-example-jar.sh
#
# 结论：Hadoop 3.3.6 的 hadoop-mapreduce-examples-3.3.6.jar 里没有名为 MergeFile 的类，
# 也不存在 mergefile 子命令。历史版本（Hadoop 0.x/1.x 的 examples.jar）里的
# org.apache.hadoop.mapred.MergeFile 已随版本迭代移除，本模块按自己的规则实现。
# 最接近的官方示例是 org.apache.hadoop.examples.MultiFileWordCount，
# 它用 CombineFileInputFormat 合并多个小文件，可作为"多文件输入"写法的参考。
set -uo pipefail

EXAMPLES_JAR=/opt/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar

[[ -f "$EXAMPLES_JAR" ]] || { echo "找不到 $EXAMPLES_JAR" >&2; exit 1; }

echo "=== examples JAR 里含 merge / combine 字样的条目 ==="
jar tf "$EXAMPLES_JAR" | grep -iE 'merge|combine' || echo "（没有）"

echo
echo "=== examples JAR 里全部顶层示例类 ==="
jar tf "$EXAMPLES_JAR" | grep -E '\.class$' | grep -v '\$' | sort

echo
echo "=== 整个 Hadoop 安装里是否还有名为 MergeFile 的类 ==="
found=0
while IFS= read -r jar_file; do
    if jar tf "$jar_file" 2>/dev/null | grep -qi 'mergefile'; then
        echo "$jar_file"
        jar tf "$jar_file" | grep -i mergefile | head -5
        found=1
    fi
done < <(find /opt/hadoop/share -name '*.jar')
[[ "$found" -eq 0 ]] && echo "（没有）"
