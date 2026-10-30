# WordCount 测试结果

负责人：6 号 · 分支：`feat/wordcount`

本文件记录**实际执行过**的测试与结果。没跑过的项一律标“待执行”，不预先写成通过。

## 1. 分两阶段

| 阶段 | 前提 | 能测什么 |
| --- | --- | --- |
| 阶段一：代码与脚本自检 | 只需要 Bash，不需要集群 | 脚本接口、语法、换行、参数校验、`verify.sh` 的比对逻辑、大数据集预期生成 |
| 阶段二：真实集群联调 | 3 号 HDFS、4 号 YARN 就绪，2 号三节点容器可起 | build、真实 MapReduce 作业、双 Worker 参与、结果核对、失败用例 |

## 2. 阶段一：已执行（本机，2026-10-30）

环境说明：开发机当时只有 Git，Docker 与 WSL2 尚未安装，因此阶段一用**不依赖 Hadoop 的部分**验证：
`verify.sh` 在本地模式下只需要 `cat`、`awk`、`diff`、`sort`，可以直接拿人工构造的 `part-r-*` 喂进去。

### 2.1 脚本接口检查

命令：`bash tests/wordcount/check-script-contract.sh`

| 检查项 | 结果 |
| --- | --- |
| 三个脚本存在 | PASS |
| 换行为 LF（无 CR） | PASS |
| `bash -n` 语法检查 | PASS |
| `run.sh` 参数个数 0 / 1 / 3 时返回非 0 | PASS（退出码 2） |
| `verify.sh` 参数个数 0 / 2 时返回非 0 | PASS（退出码 2） |
| 未编译时 `run.sh` 明确失败 | PASS（退出码 2） |

汇总：`PASS=15 FAIL=0`。

### 2.2 verify.sh 的比对逻辑

用人工构造的输出目录（模拟多个 Reduce 任务的 `part-r-00000`、`part-r-00001`）测试：

| 场景 | 构造内容 | 期望 | 实际 |
| --- | --- | --- | --- |
| 正确结果 | 两个 part 文件，合计 hadoop=2 hello=2 world=1 | 通过 | PASS，退出码 0，正确列出 3 个单词 |
| 次数错 | hadoop=3 | 失败 | PASS（正确判失败），退出码 1，diff 指出 `-hadoop 2 / +hadoop 3` |
| 少一个词 | 只有 hadoop、hello | 失败 | 退出码 1，指出缺 `world 1` |
| 多一个词 | 多出 `extra 1` | 失败 | 退出码 1，指出多余 `extra 1` |
| 只有 `_SUCCESS`、没有 part 文件 | 空目录 + 标记 | 失败 | 退出码 1，提示“没有 part-r-* 结果文件” |
| 目录不存在 | — | 失败 | 退出码 1 |
| 自定义预期文件（空格分隔） | `hadoop 2` 等 | 通过 | 退出码 0 |

这一组证明了 `verify.sh` **不是只检查 `_SUCCESS` 是否存在**，而是真的逐词比对。

### 2.3 大数据集预期生成

命令：`bash tests/wordcount/gen-large-input.sh 5 2000`

| 指标 | 结果 |
| --- | --- |
| 生成文件数 | 5 |
| 不同单词数 | 12（11 个词表单词 + `quoted`） |
| 单词总出现次数 | 41755 |
| 交叉校验 | 用 `cat ... | wc -w` 独立数一遍，同样是 41755，与 `tr/sort/uniq` 统计一致 |

## 3. 阶段一点五：统一开发容器内实测（2026-10-30 已完成）

前提：公共环境第 1—8 步走通，`hadoop-base:v0.1` 已导入（2.55 GB），容器内 `pwd` = `/workspace`、
Java `1.8.0_442`、`Hadoop 3.3.6`、基础校验输出 `BASE_API_PASS`。

集群（HDFS / YARN）当时还没起，所以这一轮用 `WORDCOUNT_LOCAL=1` 本地模式跑真实 MapReduce
（LocalJobRunner，走真实的 Mapper / Combiner / Reducer / Shuffle，只是不经过 YARN）。
输出写在 `/workspace/runtime/wc/`（该目录被 `.gitignore` 忽略，且因仓库挂载到容器而跨次保留）。

| 编号 | 项目 | 命令 | 结果 |
| --- | --- | --- | --- |
| L1 | 编译 | `bash apps/wordcount/build.sh` | PASS，`BUILD PASS`，产出 `build/wordcount.jar` |
| L2 | 固定样例 | `WORDCOUNT_LOCAL=1 bash run.sh /workspace/apps/wordcount/input /workspace/runtime/wc/fixed` | 退出码 0，`RUN PASS` |
| L3 | 核对固定样例 | `WORDCOUNT_LOCAL=1 bash verify.sh /workspace/runtime/wc/fixed` | `VERIFY PASS: 3 个单词与预期完全一致（结果文件 2 个）` |
| L4 | 边界用例 | 输入 `tests/wordcount/cases/edge`，预期 `cases/expected/edge.tsv` | `VERIFY PASS: 5 个单词与预期完全一致` |
| L5 | 大数据量 | `gen-large-input.sh 5 2000` 后跑本地作业 | `VERIFY PASS: 12 个单词与预期完全一致` |
| L6 | 拒绝覆盖 | 对已存在的输出目录再跑一次 `run.sh` | 退出码 2，`RUN FAIL: 本地输出已存在，拒绝覆盖` |

L3 的实际输出（两个 Reduce 任务各写一个 part 文件，合计结果）：

```
hadoop   2
hello    2
world    1
```

L4 的实际输出（大小写归一、标点作分隔、空行跳过、纯数字与中文都按同一规则处理）：

```
2026     2
hadoop   6
hello    3
分析     1
数据     3
```

L5 的交叉校验：不用 Java，直接用 `tr / sort / uniq` 把 5 个输入文件独立统计一遍，
得到 12 个单词、41755 次出现，与 Java 作业输出逐词完全一致。

### 3.1 本轮实测中发现并修复的问题

| 问题 | 现象 | 原因 | 修法 |
| --- | --- | --- | --- |
| 本地模式路径拼接错 | `file://workspace/...`，作业报参数错误 | `to_uri` 把 `file://` 末尾斜杠去掉再拼绝对路径，只剩两个斜杠，`workspace` 被当成主机名 | 新增 `local_to_uri`，绝对路径统一补成 `file:///a/b` |
| `hadoop jar` 参数错位 | 无论传几个参数，驱动都打印用法并返回 2 | `build.sh` 用 `jar cfe` 往清单里写了 `Main-Class`，`hadoop jar <jar> <主类> ...` 时主类名不再被当成主类，而成了第一个业务参数 | 改用 `jar cf`，不写 `Main-Class`，与仓库既有约定一致 |
| 预期文件带 BOM | 边界用例首个单词对不上：`-﻿2026 / +2026` | 预期 TSV 被以带 BOM 的 UTF-8 保存，第一个单词前面多了不可见字符 | 去掉两个预期文件的 BOM，并在 `verify.sh` 解析时兜底剥除行首 BOM |

## 4. 阶段二：真实集群联调（2026-10-30 已完成）

集群用仓库自带的 `compose/distributed.yaml` 起三节点（master、worker1、worker2），镜像 `hadoop-base:v0.1`。
启动后先确认服务真的注册上了，而不是容器起来就算：

```
hdfs dfsadmin -report  ->  Live datanodes (2): worker1、worker2
yarn node -list        ->  Total Nodes:2，worker1、worker2 均为 RUNNING
```

下列命令都在 master 容器内、项目根目录 `/workspace` 执行。

| 编号 | 项目 | 命令 | 结果 |
| --- | --- | --- | --- |
| C1 | 编译 | `bash apps/wordcount/build.sh` | PASS，`BUILD PASS` |
| C2 | 上传固定输入 | `hdfs dfs -put -f apps/wordcount/input/*.txt /project/input/wordcount` | 2 个文件，19 + 13 字节 |
| C3 | 运行固定小样例 | `bash apps/wordcount/run.sh /project/input/wordcount /project/output/wordcount/run-001` | `RUN PASS`，作业 completed successfully |
| C4 | 核对结果 | `bash apps/wordcount/verify.sh /project/output/wordcount/run-001` | `VERIFY PASS: 3 个单词与预期完全一致（结果文件 2 个）` |
| C5 | 查看输出 | `hdfs dfs -cat '/project/output/wordcount/run-001/part-r-*'` | `hadoop 2 / hello 2 / world 1` |
| C6 | 边界输入 | `bash tests/wordcount/check-edge-cases.sh` | `EDGE CASES PASS`，5 个单词与预期一致 |
| C7 | 大数据 + 双 Worker | `bash tests/wordcount/check-large.sh 5 2000` | `LARGE INPUT PASS`，12 个单词、2 个 part 文件 |
| C8 | 失败用例 | `bash tests/wordcount/check-failure-cases.sh` | `PASS=5 FAIL=0`，`FAILURE CASES PASS` |
| C9 | 自带示例对照 | `hadoop jar hadoop-mapreduce-examples-3.3.6.jar wordcount` 跑同一输入 | 与本模块输出**逐行完全一致** |
| C10 | 本地模式调试 | `WORDCOUNT_LOCAL=1 bash run.sh ...` | 见第 3 节 L2—L6 |

C3 的实际输出正好是固定样例应有的三个词：

```
hadoop   2
hello    2
world    1
```

### 4.1 分布式执行的证据（C7）

输入是 5 个文件（`gen-large-input.sh 5 2000` 生成，共 41755 个单词）。

**证据一：application id 与任务数**

```
job_1793364628657_0002
Launched map tasks=5
Launched reduce tasks=2
```

**证据二：每个任务跑在哪个节点**（读两个 worker 上 NodeManager 的容器日志目录，
按容器里的 `attempt_` 编号对应任务）

| 节点 | 容器 | 对应任务 |
| --- | --- | --- |
| worker1 | container_..._01_000002 | `m_000000` Map |
| worker1 | container_..._01_000003 | `m_000001` Map |
| worker1 | container_..._01_000004 | `m_000002` Map |
| worker1 | container_..._01_000007 | `r_000000` Reduce |
| worker2 | container_..._01_000005 | `m_000003` Map |
| worker2 | container_..._01_000006 | `m_000004` Map |
| worker2 | container_..._01_000008 | `r_000001` Reduce |

Map 任务 3 个在 worker1、2 个在 worker2；Reduce 任务两个节点各 1 个。
**两个 Worker 都真实参与了 Map 和 Reduce**，不是只有 DataNode 在线。

**证据三：输出侧**

```
hdfs dfs -ls /project/output/wordcount/large-001 | grep -c part-r-  ->  2
VERIFY PASS: 12 个单词与预期完全一致（结果文件 2 个）
```

### 4.2 联调中顺带验证到的行为

- 对已存在的输出目录重跑 `run.sh`：退出码 2，旧数据未被删除（`check-failure-cases.sh` 第 2 项专门核对了这一点）。
- 输入路径不存在：退出码 2，不会去提交一个注定失败的作业。
- `verify.sh` 对不存在的输出目录返回 1，对错误预期返回 1。

## 5. 复现步骤

不需要集群的部分，任何人都能复现：

```bash
bash tests/wordcount/check-script-contract.sh
bash tests/wordcount/gen-large-input.sh 5 2000
```

统一开发容器内复现真实作业（第 3 节那批）：

```bash
cd /workspace
bash apps/wordcount/build.sh
WORDCOUNT_LOCAL=1 bash apps/wordcount/run.sh  /workspace/apps/wordcount/input /workspace/runtime/wc/fixed
WORDCOUNT_LOCAL=1 bash apps/wordcount/verify.sh /workspace/runtime/wc/fixed
```

在三节点集群上复现第 4 节（在宿主机项目根目录执行，Git Bash 下要 `export MSYS_NO_PATHCONV=1`，
否则 `/workspace/...` 这类容器内路径会被改写成 Windows 路径）：

```bash
docker compose --env-file .development -f compose/distributed.yaml run --rm master \
  bash /workspace/scripts/hadoop-node.sh init-namenode      # 只在首次或换卷时执行
docker compose --env-file .development -f compose/distributed.yaml up -d
docker exec compose-master-1 bash -lc 'cd /workspace && bash tests/wordcount/check-large.sh 5 2000'
```
