#!/usr/bin/env bash
#
# 编译 WordCount 源码并打包成 build/wordcount.jar。
#
# 接口（见 docs/interfaces.md）：
#   bash apps/wordcount/build.sh     无参数；成功返回 0，失败返回非 0
# 产物：
#   apps/wordcount/build/classes/    编译后的 class 文件
#   apps/wordcount/build/wordcount.jar  作业 Jar
# 说明：
#   - 基础镜像没有 Maven，直接用镜像自带的 javac、jar，编译类路径取自 hadoop classpath。
#   - 脚本自行定位所在目录，从任意当前目录调用都有效。
#   - build/ 已被 .gitignore 忽略，编译产物不会进入仓库。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# 读取公共契约（HADOOP_HOME、WORKSPACE 等），与全组保持同一份路径约定。
if [ -f "${PROJECT_ROOT}/.development" ]; then
    # shellcheck disable=SC1091
    . "${PROJECT_ROOT}/.development"
fi

HADOOP_HOME="${HADOOP_HOME:-/opt/hadoop}"
HADOOP_BIN="${HADOOP_HOME}/bin/hadoop"
JAVAC_BIN="${JAVA_HOME:-/opt/java/openjdk}/bin/javac"
JAR_BIN="${JAVA_HOME:-/opt/java/openjdk}/bin/jar"

SRC_DIR="${SCRIPT_DIR}/src"
BUILD_DIR="${SCRIPT_DIR}/build"
CLASSES_DIR="${BUILD_DIR}/classes"
JAR_FILE="${BUILD_DIR}/wordcount.jar"

fail() {
    echo "BUILD FAIL: $*" >&2
    exit 1
}

[ -d "${SRC_DIR}" ] || fail "找不到源码目录 ${SRC_DIR}"
[ -x "${JAVAC_BIN}" ] || fail "找不到 javac：${JAVAC_BIN}（请确认在统一开发容器内执行）"
[ -x "${JAR_BIN}" ] || fail "找不到 jar：${JAR_BIN}（请确认在统一开发容器内执行）"
[ -x "${HADOOP_BIN}" ] || fail "找不到 hadoop：${HADOOP_BIN}（请先完成公共环境第 6 步导入镜像）"

# 从 hadoop classpath 取 Hadoop 依赖，不额外引入第三方库。
HADOOP_CLASSPATH="$("${HADOOP_BIN}" classpath 2>/dev/null)" || fail "无法获取 hadoop classpath"
[ -n "${HADOOP_CLASSPATH}" ] || fail "hadoop classpath 输出为空"

# 收集源文件；用数组传递，避免路径含空格时被拆开。
SOURCES=()
while IFS= read -r java_file; do
    SOURCES+=("${java_file}")
done < <(find "${SRC_DIR}" -type f -name '*.java' | sort)

[ "${#SOURCES[@]}" -gt 0 ] || fail "${SRC_DIR} 下没有 Java 源文件"

# 每次全量重编，避免增量残留的旧 class 混进 Jar。
rm -rf "${CLASSES_DIR}"
mkdir -p "${CLASSES_DIR}"

echo "[1/2] javac ${#SOURCES[@]} 个源文件"
"${JAVAC_BIN}" \
    -encoding UTF-8 \
    -source 8 -target 8 -Xlint:-options \
    -classpath "${HADOOP_CLASSPATH}" \
    -d "${CLASSES_DIR}" \
    "${SOURCES[@]}"

echo "[2/2] jar -> ${JAR_FILE}"
# 不写 Main-Class：hadoop jar 只有在清单没有 Main-Class 时才会把第一个参数当主类，
# 写了 Main-Class 会把 run.sh 传来的主类名当成业务参数，导致参数个数不对。
"${JAR_BIN}" cf "${JAR_FILE}" -C "${CLASSES_DIR}" .

echo "BUILD PASS: ${JAR_FILE}"
