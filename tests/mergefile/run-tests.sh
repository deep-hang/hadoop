#!/usr/bin/env bash
# MergeFile 模块测试：多文件输入、合并语义与结果。
#
# 用法：
#   bash tests/mergefile/run-tests.sh            # 默认本地模式：file:// 文件系统 + local JobRunner
#   bash tests/mergefile/run-tests.sh --hdfs     # 正式集群模式：真实 HDFS/YARN
#
# 本地模式可在公共开发容器内直接运行，不需要三节点集群。
# 本地模式只写临时目录；集群模式只写 /project/output/mergefile-test/run-<时间戳>，
# 两种模式都不会删除已有数据。任何用例失败时脚本返回非零退出码。
set -uo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$TEST_DIR/../.." && pwd)"
APP_DIR="$REPO_DIR/apps/mergefile"
EXPECTED_FILE="$APP_DIR/expected/merged-small.txt"
INPUT_DIR="$APP_DIR/input"

MODE="local"
case "${1:-}" in
    --hdfs) MODE="hdfs" ;;
    --local | "") MODE="local" ;;
    *)
        echo "用法: bash $(basename "$0") [--local|--hdfs]" >&2
        exit 2
        ;;
esac

PASSED=0
FAILED=0

# 本地临时目录：存放测试脚本自己产生的中间文件，两种模式都在本地文件系统
WORK="$(mktemp -d /tmp/mergefile-tests-XXXXXX)"
LOG_DIR="$(mktemp -d /tmp/mergefile-logs-XXXXXX)"
STAGE_DIR="$WORK/stage"
mkdir -p "$STAGE_DIR"

# ROOT 是本模块在当前文件系统里的根目录：
#   本地模式 = 本地临时目录（file:// 文件系统）
#   集群模式 = HDFS 目录
if [[ "$MODE" == "local" ]]; then
    ROOT="$WORK/fs"
else
    ROOT="/project/output/mergefile-test/run-$(date +%Y%m%d-%H%M%S)"
fi

pass() {
    PASSED=$((PASSED + 1))
    echo "  PASS  $1"
}

fail() {
    FAILED=$((FAILED + 1))
    echo "  FAIL  $1"
}

section() {
    echo
    echo "== $1 =="
}

cleanup() {
    rm -rf "$WORK" "$LOG_DIR"
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# 文件系统辅助函数：本地模式用 file://，集群模式用 HDFS
# ---------------------------------------------------------------------------

# 逻辑路径 -> 当前文件系统里的路径
path_of() {
    if [[ "$MODE" == "local" ]]; then
        echo "file://$1"
    else
        echo "$1"
    fi
}

# 去掉 file:// 前缀，得到本地可访问的路径（只在本地模式使用）
to_local() {
    local path="$1"
    printf '%s' "${path#file://}"
}

# 路径是否存在于当前文件系统
path_exists() {
    local path="$1"
    if [[ "$MODE" == "local" ]]; then
        [[ -e "$(to_local "$path")" ]]
    else
        hdfs dfs -test -e "$path" >/dev/null 2>&1
    fi
}

# 文件是否存在且内容为空
file_is_empty() {
    local path="$1"
    if [[ "$MODE" == "local" ]]; then
        local local_path
        local_path="$(to_local "$path")"
        [[ -f "$local_path" && ! -s "$local_path" ]]
    else
        hdfs dfs -test -e "$path" >/dev/null 2>&1 || return 1
        [[ -z "$(hdfs dfs -cat "$path" 2>/dev/null)" ]]
    fi
}

# 把当前文件系统上的文件取到本地，供内容比较使用
fetch_file() {
    local source_path="$1"
    local destination="$2"
    if [[ "$MODE" == "local" ]]; then
        cp -f "$(to_local "$source_path")" "$destination" 2>/dev/null || return 1
    else
        hdfs dfs -get -f "$source_path" "$destination" >/dev/null 2>&1 || return 1
    fi
}

# 读取当前文件系统上的文件内容
read_file() {
    local path="$1"
    if [[ "$MODE" == "local" ]]; then
        cat "$(to_local "$path")" 2>/dev/null
    else
        hdfs dfs -cat "$path" 2>/dev/null
    fi
}

# 在当前文件系统上创建目录
make_dir() {
    local path="$1"
    if [[ "$MODE" == "local" ]]; then
        mkdir -p "$(to_local "$path")"
    else
        hdfs dfs -mkdir -p "$path" >/dev/null
    fi
}

# 把本地文件写入当前文件系统
put_file() {
    local source_file="$1"
    local target_path="$2"
    if [[ "$MODE" == "local" ]]; then
        mkdir -p "$(dirname "$(to_local "$target_path")")"
        cp -f "$source_file" "$(to_local "$target_path")" || return 1
    else
        hdfs dfs -mkdir -p "$(dirname "$target_path")" >/dev/null 2>&1
        hdfs dfs -put -f "$source_file" "$target_path" >/dev/null 2>&1 || return 1
    fi
}

# 在当前文件系统上复制文件
copy_file() {
    local source_path="$1"
    local target_path="$2"
    if [[ "$MODE" == "local" ]]; then
        mkdir -p "$(dirname "$(to_local "$target_path")")"
        cp -f "$(to_local "$source_path")" "$(to_local "$target_path")" || return 1
    else
        local temporary
        temporary="$(mktemp)"
        hdfs dfs -get -f "$source_path" "$temporary" >/dev/null 2>&1 \
            || { rm -f "$temporary"; return 1; }
        hdfs dfs -mkdir -p "$(dirname "$target_path")" >/dev/null 2>&1
        hdfs dfs -put -f "$temporary" "$target_path" >/dev/null 2>&1 \
            || { rm -f "$temporary"; return 1; }
        rm -f "$temporary"
    fi
}

# 修改当前文件系统上的文件：先取到本地，改完再写回
transform_file() {
    local path="$1"
    local command="$2"
    local temporary
    temporary="$(mktemp)"
    if ! fetch_file "$path" "$temporary"; then
        rm -f "$temporary"
        return 1
    fi
    if ! bash -c "$command" mergefile-transform "$temporary"; then
        rm -f "$temporary"
        return 1
    fi
    if ! put_file "$temporary" "$path"; then
        rm -f "$temporary"
        return 1
    fi
    rm -f "$temporary"
}

# 把本地目录的内容同步到当前文件系统
sync_dir() {
    local source_dir="$1"
    local target_dir="$2"
    if [[ "$MODE" == "local" ]]; then
        make_dir "$target_dir"
        cp -f "$source_dir"/* "$(to_local "$target_dir")"/ 2>/dev/null || true
    else
        hdfs dfs -mkdir -p "$target_dir" >/dev/null
        hdfs dfs -put -f "$source_dir"/* "$target_dir"/ >/dev/null
    fi
}

run_app() {
    # run_app <输入路径> <输出路径> <日志文件>
    bash "$APP_DIR/run.sh" "$1" "$2" >"$3" 2>&1
}

verify_app() {
    bash "$APP_DIR/verify.sh" "$1" >"$2" 2>&1
}

# 断言文件内容与固定预期一致（逐字节比较）
expect_content() {
    local description="$1"
    local actual_path="$2"
    local expected_file="$3"
    local actual_file
    actual_file="$(mktemp)"
    if ! fetch_file "$actual_path" "$actual_file"; then
        fail "$description（取不到结果文件 $actual_path）"
        rm -f "$actual_file"
        return
    fi
    if diff -u "$expected_file" "$actual_file" >/dev/null 2>&1; then
        pass "$description"
    else
        fail "$description"
        diff -u "$expected_file" "$actual_file" | sed 's/^/        /' | head -20
    fi
    rm -f "$actual_file"
}

# 断言命令的退出码
expect_exit_code() {
    local description="$1"
    local expected_code="$2"
    shift 2
    "$@" >/dev/null 2>&1
    local actual_code=$?
    if [[ "$actual_code" -eq "$expected_code" ]]; then
        pass "$description（退出码 $actual_code）"
    else
        fail "$description（期望退出码 $expected_code，实际 $actual_code）"
    fi
}

# 故意破坏结果文件，并断言破坏成功
corrupt_file() {
    local description="$1"
    local path="$2"
    local command="$3"
    if transform_file "$path" "$command" >/dev/null 2>&1; then
        pass "$description"
    else
        fail "$description（无法修改结果文件）"
    fi
}

# ---------------------------------------------------------------------------
section "准备：编译应用"
# ---------------------------------------------------------------------------
if bash "$APP_DIR/build.sh" >"$LOG_DIR/build.log" 2>&1; then
    pass "build.sh 编译成功"
else
    fail "build.sh 编译失败，详见 $LOG_DIR/build.log"
    echo "测试中止：没有应用产物，后续用例无法执行。"
    exit 1
fi

# ---------------------------------------------------------------------------
section "用例 1：固定小样例（多文件 + 跨文件重复 + 空行 + 首尾空白 + 大小写）"
# ---------------------------------------------------------------------------
case1_in="$ROOT/case1-in"
case1_out="$ROOT/case1-out"
sync_dir "$INPUT_DIR" "$case1_in"

if run_app "$(path_of "$case1_in")" "$(path_of "$case1_out")" "$LOG_DIR/case1.log"; then
    pass "run.sh 处理多个输入文件成功"
else
    fail "run.sh 处理多个输入文件失败，详见 $LOG_DIR/case1.log"
fi

if path_exists "$(path_of "$case1_out/merged.txt")"; then
    pass "输出目录生成唯一结果文件 merged.txt"
else
    fail "输出目录缺少 merged.txt"
fi

if path_exists "$(path_of "$case1_out/_SUCCESS")"; then
    pass "输出目录带 _SUCCESS 标记"
else
    fail "输出目录缺少 _SUCCESS 标记"
fi

expect_content "合并结果与固定预期完全一致" "$(path_of "$case1_out/merged.txt")" "$EXPECTED_FILE"

expect_exit_code "verify.sh 核对固定小样例通过" 0 verify_app "$(path_of "$case1_out")" "$LOG_DIR/case1-verify.log"

# MapReduce 各阶段计数：12 行输入 -> 10 条记录 -> 5 条唯一记录，3 个 Map 任务
if grep -q "Map input records=12" "$LOG_DIR/case1.log" \
    && grep -q "Map output records=10" "$LOG_DIR/case1.log" \
    && grep -q "Reduce input groups=5" "$LOG_DIR/case1.log" \
    && grep -q "Reduce output records=5" "$LOG_DIR/case1.log"; then
    pass "MapReduce 计数正确：输入 12 行、记录 10 条、唯一记录 5 条"
else
    fail "MapReduce 计数与预期不符，详见 $LOG_DIR/case1.log"
fi

if grep -q "Shuffled Maps =3" "$LOG_DIR/case1.log"; then
    pass "3 个输入文件产生 3 个 Map 任务"
else
    fail "Map 任务数不是 3，详见 $LOG_DIR/case1.log"
fi

# 跨文件重复：apple / banana 各 3 次且来源覆盖 3 个文件
case1_actual="$(mktemp)"
fetch_file "$(path_of "$case1_out/merged.txt")" "$case1_actual"
if grep -q "^apple	3	a.txt,b.txt,c.txt$" "$case1_actual" \
    && grep -q "^banana	3	a.txt,b.txt,c.txt$" "$case1_actual" \
    && grep -q "^date	2	b.txt,c.txt$" "$case1_actual"; then
    pass "跨文件重复记录次数与来源文件正确"
else
    fail "跨文件重复记录次数或来源文件不正确"
fi

# 大小写敏感 + UTF-8 字节序排序
if [[ "$(head -1 "$case1_actual")" == "Apple	1	c.txt" ]] \
    && [[ "$(sed -n 2p "$case1_actual")" == "apple	3	a.txt,b.txt,c.txt" ]]; then
    pass "区分大小写，且按 UTF-8 字节序升序（Apple 在 apple 之前）"
else
    fail "大小写或排序规则不符合预期"
fi
rm -f "$case1_actual"

# 空行被丢弃：输入 12 行而输出记录 10 条
if grep -q "Map input records=12" "$LOG_DIR/case1.log" \
    && grep -q "Map output records=10" "$LOG_DIR/case1.log"; then
    pass "2 行空行被忽略，未进入合并结果"
else
    fail "空行没有被忽略"
fi

# ---------------------------------------------------------------------------
section "用例 2：单个空文件（空输入）"
# ---------------------------------------------------------------------------
case2_in="$ROOT/case2-in"
case2_out="$ROOT/case2-out"
make_dir "$case2_in"
: >"$STAGE_DIR/empty.txt"
put_file "$STAGE_DIR/empty.txt" "$case2_in/empty.txt"

expect_exit_code "run.sh 处理空文件成功（作业成功、0 条记录）" 0 \
    run_app "$(path_of "$case2_in")" "$(path_of "$case2_out")" "$LOG_DIR/case2.log"

if file_is_empty "$(path_of "$case2_out/merged.txt")"; then
    pass "空输入的结果文件存在且为空"
else
    fail "空输入的结果文件不存在或非空"
fi

expect_exit_code "verify.sh 对空输入返回非零（与固定小样例不符）" 5 \
    verify_app "$(path_of "$case2_out")" "$LOG_DIR/case2-verify.log"

# ---------------------------------------------------------------------------
section "用例 3：只含空行与空白字符的文件"
# ---------------------------------------------------------------------------
case3_in="$ROOT/case3-in"
case3_out="$ROOT/case3-out"
make_dir "$case3_in"
printf '\n   \n\t\n' >"$STAGE_DIR/blank.txt"
put_file "$STAGE_DIR/blank.txt" "$case3_in/blank.txt"

expect_exit_code "run.sh 处理纯空白文件成功" 0 \
    run_app "$(path_of "$case3_in")" "$(path_of "$case3_out")" "$LOG_DIR/case3.log"

if file_is_empty "$(path_of "$case3_out/merged.txt")"; then
    pass "纯空白输入的结果文件为空"
else
    fail "纯空白输入的结果文件不正确"
fi

# ---------------------------------------------------------------------------
section "用例 4：Windows 换行（CRLF）输入"
# ---------------------------------------------------------------------------
case4_in="$ROOT/case4-in"
case4_out="$ROOT/case4-out"
make_dir "$case4_in"
printf 'apple\r\nbanana\r\n' >"$STAGE_DIR/crlf.txt"
printf 'apple\n' >"$STAGE_DIR/lf.txt"
put_file "$STAGE_DIR/crlf.txt" "$case4_in/crlf.txt"
put_file "$STAGE_DIR/lf.txt" "$case4_in/lf.txt"

expect_exit_code "run.sh 处理 CRLF 输入成功" 0 \
    run_app "$(path_of "$case4_in")" "$(path_of "$case4_out")" "$LOG_DIR/case4.log"

# 与固定预期逐字节比较：若回车没有被去掉，diff 会立刻发现差异
expect_content "CRLF 与 LF 视为同一条记录（回车被去掉）" \
    "$(path_of "$case4_out/merged.txt")" "$TEST_DIR/expected/crlf-expected.txt"

# ---------------------------------------------------------------------------
section "用例 5：单文件输入"
# ---------------------------------------------------------------------------
case5_in="$ROOT/case5-in"
case5_out="$ROOT/case5-out"
make_dir "$case5_in"
printf 'solo\n' >"$STAGE_DIR/solo.txt"
put_file "$STAGE_DIR/solo.txt" "$case5_in/solo.txt"

expect_exit_code "run.sh 处理单文件输入成功" 0 \
    run_app "$(path_of "$case5_in")" "$(path_of "$case5_out")" "$LOG_DIR/case5.log"

if [[ "$(read_file "$(path_of "$case5_out/merged.txt")")" == "$(printf 'solo\t1\tsolo.txt')" ]]; then
    pass "单文件输入结果正确"
else
    fail "单文件输入结果不正确"
fi

# ---------------------------------------------------------------------------
section "用例 6：同一文件内重复"
# ---------------------------------------------------------------------------
case6_in="$ROOT/case6-in"
case6_out="$ROOT/case6-out"
make_dir "$case6_in"
printf 'dup\ndup\ndup\n' >"$STAGE_DIR/dup.txt"
put_file "$STAGE_DIR/dup.txt" "$case6_in/dup.txt"

expect_exit_code "run.sh 处理文件内重复成功" 0 \
    run_app "$(path_of "$case6_in")" "$(path_of "$case6_out")" "$LOG_DIR/case6.log"

if [[ "$(read_file "$(path_of "$case6_out/merged.txt")")" == "$(printf 'dup\t3\tdup.txt')" ]]; then
    pass "同一文件内重复次数累加，来源文件只出现一次"
else
    fail "文件内重复处理不正确"
fi

# ---------------------------------------------------------------------------
section "用例 7：行内空白保留（a b 与 a  b 是两条不同记录）"
# ---------------------------------------------------------------------------
case7_in="$ROOT/case7-in"
case7_out="$ROOT/case7-out"
make_dir "$case7_in"
printf 'a b\na  b\n' >"$STAGE_DIR/inner-space.txt"
put_file "$STAGE_DIR/inner-space.txt" "$case7_in/inner-space.txt"

expect_exit_code "run.sh 处理行内空白成功" 0 \
    run_app "$(path_of "$case7_in")" "$(path_of "$case7_out")" "$LOG_DIR/case7.log"

expect_content "只去掉首尾空白，行内空白保留" \
    "$(path_of "$case7_out/merged.txt")" "$TEST_DIR/expected/inner-space-expected.txt"

# ---------------------------------------------------------------------------
section "用例 8：输入路径不存在"
# ---------------------------------------------------------------------------
expect_exit_code "run.sh 对不存在的输入返回非零" 4 \
    run_app "$(path_of "$ROOT/not-exist-input")" "$(path_of "$ROOT/case8-out")" "$LOG_DIR/case8.log"

if ! path_exists "$(path_of "$ROOT/case8-out")"; then
    pass "输入不存在时没有产生输出目录"
else
    fail "输入不存在时仍然创建了输出目录"
fi

# ---------------------------------------------------------------------------
section "用例 9：输出路径已存在"
# ---------------------------------------------------------------------------
case9_out="$ROOT/case9-out"
make_dir "$case9_out"
printf 'keep-me\n' >"$STAGE_DIR/keep-me.txt"
put_file "$STAGE_DIR/keep-me.txt" "$case9_out/merged.txt"

expect_exit_code "run.sh 对已存在的输出返回非零" 5 \
    run_app "$(path_of "$case1_in")" "$(path_of "$case9_out")" "$LOG_DIR/case9.log"

if [[ "$(read_file "$(path_of "$case9_out/merged.txt")")" == "keep-me" ]]; then
    pass "已存在的输出没有被删除或覆盖"
else
    fail "已存在的输出被改动了"
fi

# ---------------------------------------------------------------------------
section "用例 10：参数错误"
# ---------------------------------------------------------------------------
expect_exit_code "run.sh 缺少参数返回非零" 2 bash "$APP_DIR/run.sh" only-one-arg
expect_exit_code "run.sh 没有参数返回非零" 2 bash "$APP_DIR/run.sh"
expect_exit_code "run.sh 输入输出相同返回非零" 2 bash "$APP_DIR/run.sh" "$ROOT/same" "$ROOT/same"
expect_exit_code "verify.sh 缺少参数返回非零" 2 bash "$APP_DIR/verify.sh"
expect_exit_code "verify.sh 参数过多返回非零" 2 bash "$APP_DIR/verify.sh" a b

# ---------------------------------------------------------------------------
section "用例 11：verify.sh 能发现被破坏的输出"
# ---------------------------------------------------------------------------
case11_out="$ROOT/case11-out"
make_dir "$case11_out"
copy_file "$case1_out/merged.txt" "$case11_out/merged.txt"
copy_file "$case1_out/_SUCCESS" "$case11_out/_SUCCESS"

expect_exit_code "verify.sh 对缺少结果文件返回非零" 4 \
    verify_app "$(path_of "$ROOT/case11-missing-out")" "$LOG_DIR/case11-missing.log"

expect_exit_code "verify.sh 对完整输出返回 0" 0 \
    verify_app "$(path_of "$case11_out")" "$LOG_DIR/case11-complete.log"

# 少一行
corrupt_file "破坏结果文件：删掉最后一行" "$case11_out/merged.txt" "sed -i '\$d' \"\$1\""
expect_exit_code "verify.sh 对缺少一行记录返回非零" 5 \
    verify_app "$(path_of "$case11_out")" "$LOG_DIR/case11-short.log"

# 恢复后打乱顺序
copy_file "$case1_out/merged.txt" "$case11_out/merged.txt"
corrupt_file "破坏结果文件：交换前两行" "$case11_out/merged.txt" \
    'other=$(mktemp); { sed -n 2p "$1"; sed -n 1p "$1"; tail -n +3 "$1"; } > "$other"; mv "$other" "$1"'
expect_exit_code "verify.sh 对顺序错误返回非零" 5 \
    verify_app "$(path_of "$case11_out")" "$LOG_DIR/case11-order.log"

# 恢复后改次数
copy_file "$case1_out/merged.txt" "$case11_out/merged.txt"
corrupt_file "破坏结果文件：把 apple 的次数改成 9" "$case11_out/merged.txt" \
    'sed -i "s/^apple\t3\t/apple\t9\t/" "$1"'
expect_exit_code "verify.sh 对次数错误返回非零" 5 \
    verify_app "$(path_of "$case11_out")" "$LOG_DIR/case11-count.log"

# 恢复后改来源文件
copy_file "$case1_out/merged.txt" "$case11_out/merged.txt"
corrupt_file "破坏结果文件：给 date 多加一个来源文件" "$case11_out/merged.txt" \
    'sed -i "s/^date\t2\t/date\t2\tx.txt/" "$1"'
expect_exit_code "verify.sh 对来源文件错误返回非零" 5 \
    verify_app "$(path_of "$case11_out")" "$LOG_DIR/case11-source.log"

# 恢复后保留未重命名的 part 文件
copy_file "$case1_out/merged.txt" "$case11_out/merged.txt"
printf 'x\n' >"$STAGE_DIR/part-r-00001"
put_file "$STAGE_DIR/part-r-00001" "$case11_out/part-r-00001"
expect_exit_code "verify.sh 对残留 part 文件返回非零" 5 \
    verify_app "$(path_of "$case11_out")" "$LOG_DIR/case11-part.log"

# ---------------------------------------------------------------------------
section "用例 12：多文件演示数据集（8 个输入文件）"
# ---------------------------------------------------------------------------
case12_in="$ROOT/case12-in"
case12_out="$ROOT/case12-out"
sync_dir "$TEST_DIR/input-multi" "$case12_in"

expect_exit_code "run.sh 处理多文件演示数据集成功" 0 \
    run_app "$(path_of "$case12_in")" "$(path_of "$case12_out")" "$LOG_DIR/case12.log"

expect_content "多文件演示数据集结果与固定预期一致" \
    "$(path_of "$case12_out/merged.txt")" "$TEST_DIR/expected/multi-expected.txt"

expect_exit_code "verify-multi.sh 核对多文件演示数据集通过" 0 \
    bash "$TEST_DIR/verify-multi.sh" "$(path_of "$case12_out")"

# 8 个输入文件 -> 8 个 Map 任务
if grep -q "Shuffled Maps =8" "$LOG_DIR/case12.log"; then
    pass "8 个输入文件产生 8 个 Map 任务"
else
    fail "Map 任务数不是 8，详见 $LOG_DIR/case12.log"
fi

# ---------------------------------------------------------------------------
echo
echo "======================================"
echo "测试模式: $MODE"
echo "通过: $PASSED    失败: $FAILED"
if [[ "$MODE" == "hdfs" ]]; then
    echo "HDFS 输出目录（保留供检查）: $ROOT"
fi
echo "======================================"
if [[ "$FAILED" -gt 0 ]]; then
    echo "RESULT: FAIL"
    exit 1
fi
echo "RESULT: PASS"
exit 0