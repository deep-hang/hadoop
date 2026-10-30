# 6 号：WordCount 单词统计

自己实现的 Hadoop MapReduce 单词统计：文本按行读入 → Mapper 切词并输出「单词, 1」→ Shuffle 按单词分组 →
Reducer 累加 → 输出「单词, 总次数」。最终在真实 HDFS / YARN 上运行，并证明两个 Worker 都参与了计算。

负责人：6 号。分支：`feat/wordcount`。接口约定见 [公共接口](../../docs/interfaces.md)；任务指南见
[模块说明](../../docs/modules/wordcount/README.md)；设计与结果见 [实现说明](../../docs/modules/wordcount/implementation.md)。

## 1. 目录内容

```text
apps/wordcount/
├── src/com/hadooplab/wordcount/
│   ├── Tokenizer.java          固定分词规则（Mapper 与测试共用同一份实现）
│   ├── WordCountMapper.java    Map 阶段：切词，输出 (单词, 1)
│   ├── WordCountReducer.java   Reduce 阶段：同词累加（同时用作 Combiner）
│   └── WordCountDriver.java    Driver：组装作业、校验参数并提交
├── input/
│   ├── a.txt                   固定小样例之一
│   └── b.txt                   固定小样例之二
├── build.sh                    编译并打包 build/wordcount.jar
├── run.sh                      提交作业：run.sh <输入> <输出>
└── verify.sh                   核对输出内容：verify.sh <输出>
```

`build/` 是编译产物目录，已被 `.gitignore` 忽略，不进入仓库。

## 2. 固定分词规则

规则只有三条，代码、输入和预期结果都以这三条为准：

1. **一个单词 = 连续的字母或数字**（Java 正则 `[\p{L}\p{N}]+`，中文等 Unicode 字母也算单词）；
2. **其他任何字符都是分隔符**：空格、制表符、逗号、句号、引号、括号、破折号等，本身不产生单词；
3. **统一转小写**（`Locale.ROOT`），因此不区分大小写，`Hello`、`HELLO`、`hello` 算同一个词。

推论：空行、纯空白行、纯标点行不含字母数字，切分后是 0 个单词，Mapper 不会输出任何记录。

### 固定小样例与预期

`input/a.txt`：

```text
hello hadoop
hello
```

`input/b.txt`：

```text
hadoop world
```

预期词频（三个词，共 5 次）：

| 单词 | 次数 |
| --- | --- |
| hadoop | 2 |
| hello | 2 |
| world | 1 |

这份预期写在 `verify.sh` 里作为默认值，同时留了一份 `tests/wordcount/cases/expected/fixed-sample.tsv` 便于手动对照。

## 3. 三个脚本怎么用

三个脚本都在**统一开发容器内**用 Bash 运行，脚本自己定位所在目录，从任意当前目录调用都有效。

### build.sh

```bash
bash /workspace/apps/wordcount/build.sh
```

用镜像自带的 `javac`、`jar` 编译（基础镜像没有 Maven），编译类路径取自 `hadoop classpath`，
产物为 `build/wordcount.jar`（带 `Main-Class`）。成功输出 `BUILD PASS`，失败非 0。

### run.sh

```bash
# 正式（HDFS / YARN）：参数按 HDFS 路径解释，自动补 .development 里的 HDFS_URI
bash /workspace/apps/wordcount/run.sh /project/input/wordcount /project/output/wordcount/run-001
```

- 输入不存在 → 非 0，并提示先 `hdfs dfs -put` 上传；
- **输出目录已存在 → 非 0，不会递归删除旧结果**，重复演示请换 `run-002`；
- 默认 Reduce 任务数为 **2**，让两个 Worker 都能领到 Reduce 任务；可用 `WORDCOUNT_REDUCERS=1` 改回单 Reduce。

本地调试模式（上游集群未就绪时验证逻辑，**不能当作 YARN 验收结果**）：

```bash
WORDCOUNT_LOCAL=1 bash /workspace/apps/wordcount/run.sh \
  /workspace/apps/wordcount/input /tmp/wordcount-local-out
```

本地模式改用 `file://` 与 `LocalJobRunner`，不连 HDFS、不占 YARN 资源。

### verify.sh

```bash
# 默认核对固定小样例（hadoop=2 hello=2 world=1）
bash /workspace/apps/wordcount/verify.sh /project/output/wordcount/run-001

# 核对其他数据集：预期文件两列「单词 制表符 次数」
WORDCOUNT_EXPECTED=tests/wordcount/cases/expected/edge.tsv \
  bash /workspace/apps/wordcount/verify.sh /project/output/wordcount/edge-001
```

核对方式：读出**全部** `part-r-*`，按单词累加，与预期逐词比对（单词集合与每个单词的次数都要一致，
多一个词、少一个词、次数不对都算失败）。只检查 `_SUCCESS` 存在不算通过——它只说明作业正常结束，
不说明结果正确。多 Reduce 任务时输出会拆成多个 `part-r-00000`、`part-r-00001`，脚本会合并统计。

## 4. 完整演示流程（集群就绪后）

在 master 容器内逐条执行：

```bash
bash /workspace/apps/wordcount/build.sh
hdfs dfs -mkdir -p /project/input/wordcount
hdfs dfs -put /workspace/apps/wordcount/input/*.txt /project/input/wordcount
bash /workspace/apps/wordcount/run.sh /project/input/wordcount /project/output/wordcount/run-001
bash /workspace/apps/wordcount/verify.sh /project/output/wordcount/run-001
hdfs dfs -cat '/project/output/wordcount/run-001/part-r-*'
```

更大规模、多文件、用于展示双 Worker 参与的流程见 `tests/wordcount/check-large.sh`。

## 5. 与 Hadoop 自带 WordCount 的关系

老师要求演示 Hadoop 自带实例，本模块另外提供一份**自己写的**实现，两者都要讲清楚：

| 对比项 | 自带示例（`hadoop jar hadoop-mapreduce-examples-*.jar wordcount`） | 本模块实现 |
| --- | --- | --- |
| 分词 | 按空白切分，`StringTokenizer`，区分大小写 | 按非字母数字切分，统一小写，保留中文与数字 |
| Combiner | 有 | 有（复用 Reducer） |
| 代码位置 | 镜像里的示例 Jar | 仓库 `apps/wordcount/src/`，可改可讲 |
| 演示作用 | 证明环境与集群正常 | 讲清 Mapper / Shuffle / Reducer / Driver 的每一步 |

自带示例的命令见 [4 号指南](../../docs/modules/yarn-mapreduce/README.md)。

## 6. 已知限制

- 分词以 Unicode 字母数字为准，不做中文分词（`数据挖掘` 算一个词，不是两个）；
- 不考虑词形还原（`running` 与 `run` 是两个词）；
- 默认不设 Reduce 数量上限，超大数据集需要按集群资源调整 `WORDCOUNT_REDUCERS`。
