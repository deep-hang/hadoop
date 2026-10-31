# WordCount 固定输入与预期结果测试

负责人：6 号。本目录存放 WordCount 的额外测试脚本与专用测试数据，用于验证固定输入、预期结果、
边界情况和失败场景。它**不替代** `apps/wordcount/` 的 `build.sh`、`run.sh`、`verify.sh` 三个接口。

执行位置统一为**项目根目录**（Windows 用 Git Bash，容器内为 `/workspace`）。任何脚本失败都返回非 0。
不要修改其他模块的测试。

## 1. 用例清单

| 脚本 | 要不要集群 | 验证什么 |
| --- | --- | --- |
| [check-script-contract.sh](check-script-contract.sh) | 不需要 | 三个脚本存在、换行为 LF、语法正确、参数个数错误时返回非 0、未编译时 run.sh 明确失败 |
| [gen-large-input.sh](gen-large-input.sh) | 不需要 | 生成多文件较大规模输入，并用 shell 工具独立算出预期词频 |
| [check-edge-cases.sh](check-edge-cases.sh) | 需要 HDFS + YARN | 大小写、标点、空行、中文、数字的边界输入 |
| [check-large.sh](check-large.sh) | 需要 HDFS + YARN | 多文件较大规模输入 + 双 Worker 参与计算的证据 |
| [check-failure-cases.sh](check-failure-cases.sh) | 需要 HDFS + YARN | 输入不存在、输出已存在、核对不存在输出、错误预期，都必须失败 |

## 2. 命令

不需要集群的两项，随时可跑：

```bash
bash tests/wordcount/check-script-contract.sh
bash tests/wordcount/gen-large-input.sh 5 2000
```

需要集群的三项，在**集群就绪且已执行 `bash apps/wordcount/build.sh`** 之后，在 master 容器内执行：

```bash
bash tests/wordcount/check-edge-cases.sh
bash tests/wordcount/check-large.sh 5 2000
bash tests/wordcount/check-failure-cases.sh
```

集群没起来时这些脚本会打印 `SKIP: HDFS 不可用` 并返回非 0，不会假装通过。

## 3. 边界输入的固定数据与预期

输入在 [cases/edge/](cases/edge/)，预期在 [cases/expected/edge.tsv](cases/expected/edge.tsv)。

| 文件 | 内容要点 | 预期 |
| --- | --- | --- |
| `case.txt` | `Hello HELLO hello` 一行三态大小写 | hello = 3 |
| `punct.txt` | 逗号、句号、感叹号、括号、连续破折号 | hadoop = 5 |
| `blank.txt` | 空行、只含空格/制表符的行、纯标点行 | 0 个单词 |
| `unicode.txt` | 中文词、英文词、年份数字 | 数据 = 3、分析 = 1、hadoop = 1、2026 = 2 |

合计预期：

| 单词 | 次数 |
| --- | --- |
| hadoop | 6 |
| hello | 3 |
| 数据 | 3 |
| 分析 | 1 |
| 2026 | 2 |

`blank.txt` 是关键用例：它证明空行和纯标点不会产出空字符串单词，否则输出里会多出一个次数很高的空键。

## 4. 较大规模输入怎么来

`gen-large-input.sh` 按固定规则生成输入，**不提交生成结果**：产物写到 `tests/wordcount/build/`，
被 `.gitignore` 的 `**/build/` 规则忽略，随时可由脚本复现。

```bash
bash tests/wordcount/gen-large-input.sh 5 2000
# GEN PASS: 5 个输入文件，不同单词 12 个，单词总出现次数 41755
#   输入目录: tests/wordcount/build/large
#   预期文件: tests/wordcount/build/expected/large.tsv
```

预期词频不是用本模块的 Java 代码算的，而是用 `tr`、`sort`、`uniq` 这套 shell 工具**独立数一遍**。
两套实现给出同一结果，才算真正对上，避免“用自己的代码验证自己的代码”。
输入全部为 ASCII 单词，此时 `[:alnum:]` 与 Java 的 `\p{L}\p{N}` 等价。

## 5. 输出目录不覆盖原则

测试脚本使用固定输出名（`run-001`、`edge-001`、`large-001`）。同名目录已存在时，`run.sh` 会直接失败
并且不会删除它。重复演示时：

- 确认旧结果不需要了，自己 `hdfs dfs -rm -r <旧目录>`；
- 或者修改测试脚本里的 `OUTPUT_DIR_HDFS` 变量换成新名字。

脚本只在明确属于自己创建的临时目录上做删除。`check-failure-cases.sh` 每次运行都会用
“日期-时间-进程号-随机数”拼出独占的目录名（如 `failure-case-guard-20261031-133056-1405-29553`），
创建前先确认它事先不存在，结束时只删这一个；本地临时文件放在 `mktemp -d` 的一次性目录里。
因此往输出根目录预置的其他文件不会被删。
