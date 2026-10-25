# 多文件输入、合并语义与结果测试

负责人：7 号。本目录存放 MergeFile 模块的测试脚本、测试数据和固定预期。

模块代码与三个应用脚本在 [apps/mergefile/](../../apps/mergefile/)；合并规则和实测记录在
[docs/modules/mergefile/](../../docs/modules/mergefile/)。

## 1. 目录内容

```text
tests/mergefile/
├── run-tests.sh              模块全部用例（本地模式 / HDFS 模式）
├── verify-multi.sh           核对多文件演示数据集的结果
├── make-multi-input.sh       生成多文件演示数据集与它的固定预期
├── run-cluster-demo.sh       起三节点集群 -> 跑作业 -> 收证据 -> 拆集群
├── run-cluster-tests.sh      在 master 容器内以 HDFS 模式跑全部用例
├── collect-evidence.sh       收集节点注册、块位置、容器所在节点等证据
├── collect-node-evidence.sh  在单个节点内打印本节点跑过的容器与任务类型
├── check-example-jar.sh      核对官方 examples JAR 里没有 MergeFile 示例
├── check-scripts.sh          核对脚本的换行符（LF）与 shebang
├── check-fixtures.sh         核对演示数据集可重复生成、字节内容正确
├── input-multi/              多文件演示数据集（8 个输入文件）
└── expected/
    ├── multi-expected.txt    多文件演示数据集的固定预期
    ├── crlf-expected.txt     CRLF 输入的固定预期
    └── inner-space-expected.txt  行内空白的固定预期
```

## 2. 前置条件

- Java、Hadoop 命令可用（在公共开发容器内执行）；
- `apps/mergefile/build.sh` 能编译成功（`run-tests.sh` 会自己先编译一次）；
- HDFS 模式额外需要能访问 HDFS 的 `hdfs` 命令。

## 3. 怎么跑

### 3.1 本地模式（默认，不需要集群）

在公共开发容器内：

```bash
bash /workspace/tests/mergefile/run-tests.sh
```

本地模式用 `file://` 文件系统和 local JobRunner，只写临时目录，跑完自动清理。
适合开发阶段快速回归。

### 3.2 HDFS 模式（真实集群）

在真实三节点集群的 master 容器内：

```bash
bash /workspace/tests/mergefile/run-tests.sh --hdfs
```

HDFS 模式把输出写在 `/project/output/mergefile-test/run-<时间戳>/`，**不会删除已有数据**，
脚本结束时会打印这个目录供检查。

> 公共验证配置（`tests/common/fixtures/cluster/`）把仓库挂成只读，`build.sh` 需要可写的
> `build/` 目录。正式集群里 `/workspace` 可写时直接跑上面的命令；用只读挂载时用
> `run-cluster-tests.sh`，它会先把 `apps/` 与 `tests/` 复制到临时目录再跑。

### 3.3 一次跑完：起集群、跑作业、收证据

在装有 Docker Compose 的电脑上：

```bash
bash tests/mergefile/run-cluster-demo.sh              # 演示 + 证据
bash tests/mergefile/run-cluster-demo.sh --tests      # 再加上 HDFS 模式的全部用例
bash tests/mergefile/run-cluster-demo.sh --keep       # 跑完不拆集群，继续查看
```

脚本复用公共验证配置（master + worker1 + worker2），用独立的 compose 项目名和独立数据卷，
不会影响其他人的集群，结束时只清理自己创建的资源。

## 4. 用例清单

| 用例 | 内容 | 期望 |
| --- | --- | --- |
| 准备 | `build.sh` 编译 | 成功，产物在 `apps/mergefile/build/` |
| 1 | 固定小样例：多文件、跨文件重复、空行、首尾空白、大小写 | 结果与 `expected/merged-small.txt` 逐字节一致；`verify.sh` 返回 0；MapReduce 计数为 12 行输入 / 10 条记录 / 5 条唯一记录 / 3 个 Map 任务 |
| 2 | 单个空文件（空输入） | `run.sh` 返回 0，结果文件存在且为空；`verify.sh` 返回 5（与固定小样例不符） |
| 3 | 只含空行与空白字符的文件 | `run.sh` 返回 0，结果文件为空 |
| 4 | Windows 换行（CRLF） | 与 `expected/crlf-expected.txt` 逐字节一致（回车被去掉） |
| 5 | 单文件输入 | 结果为 `solo\t1\tsolo.txt` |
| 6 | 同一文件内重复 | 结果为 `dup\t3\tdup.txt`（次数累加，来源只出现一次） |
| 7 | 行内空白 | `a b` 与 `a  b` 是两条记录，与 `expected/inner-space-expected.txt` 一致 |
| 8 | 输入路径不存在 | `run.sh` 返回 4，且不产生输出目录 |
| 9 | 输出路径已存在 | `run.sh` 返回 5，且原有输出内容不变 |
| 10 | 参数错误 | 少参数、多参数、输入输出相同都返回 2 |
| 11 | `verify.sh` 能发现被破坏的输出 | 少一行、顺序错、次数错、来源错、残留 `part-r-*` 文件都返回 5；缺结果文件返回 4 |
| 12 | 多文件演示数据集（8 个输入文件） | 结果与 `expected/multi-expected.txt` 逐字节一致；`verify-multi.sh` 返回 0；8 个 Map 任务 |

任何一条失败，脚本都会在结尾打印 `RESULT: FAIL` 并返回非零退出码。

## 5. 多文件演示数据集

`input-multi/` 是 8 个输入文件（`log-01.txt` … `log-08.txt`），用来演示多文件合并：

- 每个文件都含共享记录 `alpha` / `beta` / `gamma` → 跨文件重复；
- 每个文件还含两条只属于自己的记录 `partNN` → 文件内重复；
- 每个文件末尾有一行空行和一行只含空格的行 → 空行边界。

合计 56 行输入、40 条记录、11 条唯一记录。固定预期在 `expected/multi-expected.txt`：

```text
alpha	8	log-01.txt,log-02.txt,log-03.txt,log-04.txt,log-05.txt,log-06.txt,log-07.txt,log-08.txt
beta	8	log-01.txt,log-02.txt,log-03.txt,log-04.txt,log-05.txt,log-06.txt,log-07.txt,log-08.txt
gamma	8	log-01.txt,log-02.txt,log-03.txt,log-04.txt,log-05.txt,log-06.txt,log-07.txt,log-08.txt
part01	2	log-01.txt
...
part08	2	log-08.txt
```

核对命令（路径按 HDFS 解释）：

```bash
bash /workspace/tests/mergefile/verify-multi.sh /project/output/mergefile/run-002
```

需要更大或更多文件时用生成脚本重新生成（会同时刷新固定预期）：

```bash
bash /workspace/tests/mergefile/make-multi-input.sh                       # 默认 8 个文件
bash /workspace/tests/mergefile/make-multi-input.sh /tmp/大输入 32 4      # 32 个文件，每个 4 条独有记录
```

## 6. 参考来源核对

Hadoop 3.3.6 自带的 `hadoop-mapreduce-examples-3.3.6.jar` 里**没有**名为 `MergeFile` 的类，
也不存在 `mergefile` 子命令；历史版本里的 `org.apache.hadoop.mapred.MergeFile` 已被移除。
最接近的官方示例是 `org.apache.hadoop.examples.MultiFileWordCount`（用 `CombineFileInputFormat`
合并多个小文件）。用下面的脚本可以自己核对一遍：

```bash
bash /workspace/tests/mergefile/check-example-jar.sh
```

## 7. 提交前的自检

```bash
bash /workspace/tests/mergefile/check-scripts.sh     # 换行符、shebang
bash /workspace/tests/mergefile/check-fixtures.sh    # 数据集可重复生成、字节内容正确
```

Windows 上用 Git Bash 执行这些脚本；`.gitattributes` 已把 `*.sh` 固定为 LF 换行。
