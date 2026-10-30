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

## 3. 阶段二：待执行（集群就绪后填写）

下列命令需要在 master 容器内执行，结果贴在本节，并在 `docs/modules/wordcount/screenshots/` 放截图。

| 编号 | 项目 | 命令 | 结果 |
| --- | --- | --- | --- |
| C1 | 编译 | `bash /workspace/apps/wordcount/build.sh` | 待执行 |
| C2 | 上传固定输入 | `hdfs dfs -put .../input/*.txt /project/input/wordcount` | 待执行 |
| C3 | 运行固定小样例 | `bash run.sh /project/input/wordcount /project/output/wordcount/run-001` | 待执行 |
| C4 | 核对结果 | `bash verify.sh /project/output/wordcount/run-001` | 待执行 |
| C5 | 查看输出 | `hdfs dfs -cat '/project/output/wordcount/run-001/part-r-*'` | 待执行 |
| C6 | 边界输入 | `bash tests/wordcount/check-edge-cases.sh` | 待执行 |
| C7 | 大数据 + 双 Worker | `bash tests/wordcount/check-large.sh 5 2000` | 待执行 |
| C8 | 失败用例 | `bash tests/wordcount/check-failure-cases.sh` | 待执行 |
| C9 | 自带示例对照 | 见 4 号指南的命令 | 待执行 |
| C10 | 本地模式调试 | `WORDCOUNT_LOCAL=1 bash run.sh <本地输入> <本地输出>` | 待执行 |

### 分布式执行的证据要求

C7 要留下三类证据，缺一不可：

1. 作业的 application id 与 Map / Reduce 任务数（Map 数 = 输入分片数，Reduce 数 = 2）；
2. 每个 Map / Reduce Attempt 所在的节点名，**同时出现 worker1 与 worker2**；
3. 输出目录里 `part-r-*` 的个数等于 2，且内容核对通过。

只截“两个 DataNode 在线”不算计算分布的证据。

## 4. 复现步骤

任何人都能按下面两条复现阶段一的结果：

```bash
bash tests/wordcount/check-script-contract.sh
bash tests/wordcount/gen-large-input.sh 5 2000
```
