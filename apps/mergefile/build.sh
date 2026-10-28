#!/usr/bin/env bash
# 编译 MergeFile 应用：javac + jar，产物放在 apps/mergefile/build/。
# 在公共开发容器内执行：bash /workspace/apps/mergefile/build.sh
set -euo pipefail

MODULE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$MODULE_DIR/src"
BUILD_DIR="$MODULE_DIR/build"
CLASSES_DIR="$BUILD_DIR/classes"
JAR_FILE="$BUILD_DIR/mergefile.jar"
MAIN_CLASS="com.example.mergefile.MergeFileDriver"

fail() {
    echo "[mergefile][build] 错误: $*" >&2
    exit 1
}

command -v javac >/dev/null 2>&1 || fail "找不到 javac，请在公共开发容器内执行"
command -v jar >/dev/null 2>&1 || fail "找不到 jar，请在公共开发容器内执行"
command -v hadoop >/dev/null 2>&1 || fail "找不到 hadoop 命令，请在公共开发容器内执行"

CLASSPATH="$(hadoop classpath --glob)"
[[ -n "$CLASSPATH" ]] || fail "无法获取 hadoop classpath"

SOURCES=()
while IFS= read -r source_file; do
    SOURCES+=("$source_file")
done < <(find "$SRC_DIR" -type f -name '*.java' | sort)
((${#SOURCES[@]} > 0)) || fail "src/ 下没有找到 Java 源文件"

rm -rf "$CLASSES_DIR"
mkdir -p "$CLASSES_DIR"

echo "[mergefile][build] 编译 ${#SOURCES[@]} 个源文件"
# -Xlint:-path: 公共镜像的 hadoop classpath 里有几个已下线的 jaxb jar，javac 会报 [path] 告警，与本模块代码无关。
javac -encoding UTF-8 -Xlint:all,-path -cp "$CLASSPATH" -d "$CLASSES_DIR" "${SOURCES[@]}"

rm -f "$JAR_FILE"
# 不在清单里写 Main-Class：hadoop jar <jar> <主类> <参数> 时，Hadoop 3.3.6 的 RunJar
# 只有在清单没有 Main-Class 时才把第一个参数当作主类，调用方式与官方 examples 一致。
jar cf "$JAR_FILE" -C "$CLASSES_DIR" .

echo "[mergefile][build] 编译完成: $JAR_FILE"
