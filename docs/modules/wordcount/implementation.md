# WordCount 实例设计与实现说明

负责人：6 号 · 分支：`feat/wordcount` · 对应 PPT 第 1—12 项

## 1. 实例目的

WordCount 是 MapReduce 的“冒烟测试”：它足够简单，能把 MapReduce 的四个角色（Mapper、Shuffle、
Reducer、Driver）全部走一遍；又足够完整，能在三节点集群上真实体现**数据分布**（输入文件的不同分片
落在 worker1 / worker2）和**计算分布**（Map、Reduce 任务分别由两个 NodeManager 承担）。

所以本实例的验收目标不是“输出 hello 3”这种结果，而是**结果正确 + 两个 Worker 确实参与了计算**，
并且整条链路（编译 → 上传 HDFS → 提交作业 → 输出核对）都能由仓库内容复现。

## 2. 输入数据设计

### 固定小样例（默认核对对象）

| 文件 | 内容 |
| --- | --- |
| `input/a.txt` | `hello hadoop` / `hello` |
| `input/b.txt` | `hadoop world` |

预期：`hadoop=2`、`hello=2`、`world=1`。

设计意图：

- 两个文件，覆盖“多输入文件”这一基本情形，Map 任务至少能拆成两个分片；
- 单词在文件之间**交叉出现**（`hadoop` 同时出现在 a.txt 和 b.txt），能证明 Shuffle 真的把
  来自不同 Map 任务的同名单词合并到了一起，而不是各自输出；
- `hello` 在 a.txt 内出现两次，能证明同一个 Map 任务内的累加（Combiner）也在工作；
- 只用一个文件测，就看不到跨文件合并；只用不重复的词，就看不到累加。三个词、两个文件刚好卡住这两个点。

### 较大规模演示数据

`tests/wordcount/gen-large-input.sh` 生成 5 个文件 × 2000 行，词表 11 个单词。用途是把 Map 任务数
拉起来，让两个 Worker 都分到任务。生成结果不入库，预期词频用 shell 工具独立统计（见测试说明）。

## 3. 分词规则（代码、输入、预期三方一致的唯一依据）

| 规则 | 说明 |
| --- | --- |
| 单词边界 | 连续的字母或数字，正则 `[\p{L}\p{N}]+` |
| 分隔符 | 其他所有字符：空格、制表符、标点、引号、括号、破折号 |
| 大小写 | 统一转小写（`Locale.ROOT`），不区分大小写 |
| 空行 / 纯标点 | 切出 0 个单词，Mapper 不输出任何记录 |

规则集中实现在 `Tokenizer.java` 一个类里，而不是散在 Mapper 里。这样预期结果、边界用例和 Mapper
引用的是同一份定义，讲课时也只需要看这一个类。

**为什么不用 `String.split`**：分隔符是“连续的非字母数字串”，用 `Pattern.matcher().find()` 顺序取出
单词更直观，也不会在同一条记录里产出空字符串碎片（`split` 对连续分隔符会给出空串）。

**为什么用 `Locale.ROOT` 而不是默认区域**：`toLowerCase()` 不带参数时受 JVM 默认区域影响，
土耳其语区域下 `I` 会转成 `ı` 而不是 `i`，同一个作业在不同节点上可能给出不同结果。显式指定
`Locale.ROOT` 才能保证多节点结果一致。

## 4. 一条数据怎么走完全程

以固定小样例的 `a.txt` 第二行 `hello` 为例：

```text
HDFS 上的 a.txt
   │  InputFormat 按行读
   ▼
Mapper:  "hello hadoop" -> (hello,1) (hadoop,1)
         "hello"        -> (hello,1)
   │
   ▼
Combiner（本模块复用 Reducer）: 同一 Map 内先合并 -> (hello,2) (hadoop,1)
   │
   ▼
Shuffle: 按单词的哈希分区、排序、分组，把同名单词送到同一个 Reduce 任务
         hello  -> [2]（来自 a.txt 的 Map）
         hadoop -> [1]（来自 a.txt 的 Map） + [1]（来自 b.txt 的 Map）
   │
   ▼
Reducer: 累加 -> (hello,2) (hadoop,2) (world,1)
   │
   ▼
输出: part-r-00000 / part-r-00001（TextOutputFormat，单词 \t 次数）
```

`hadoop` 这一条最能说明问题：它在两个不同的 Map 任务里各出现一次，最后合并成 2，这就是 Shuffle
存在的意义。PPT 里建议就用这一个词讲 Shuffle。

## 5. 四个类的职责

| 类 | 职责 | 关键点 |
| --- | --- | --- |
| `Tokenizer` | 把一行文本切成小写单词列表 | 规则唯一实现处 |
| `WordCountMapper` | 对每行切词，输出 `(单词, 1)` | 复用同一个 `Text` 对象，避免每行新建对象 |
| `WordCountReducer` | 同名单词的计数累加 | 同时注册为 Combiner，输入输出类型与 Reduce 一致 |
| `WordCountDriver` | 校验参数、检查输出目录、组装 Job、提交并等待 | 实现 `Tool` + `ToolRunner`，支持 `-D` 参数 |

### 为什么用 Combiner

Combiner 在 Map 端先做一次局部累加，Shuffle 传输的数据量从“每个单词一条”降到“每个 Map 每个单词一条”。
单词计数满足结合律和交换律（先加后加结果相同），所以 Combiner 不改变最终结果，只减少网络传输。
这也解释了为什么在本模块里 Combiner 可以直接复用 Reducer 类——输入输出类型完全一致。

### 为什么默认 2 个 Reduce 任务

一个 Reduce 任务只能跑在一个节点上。若设成 1，所有 Reduce 计算都落在同一个 Worker 上，“计算分布”
就退化成了“Map 分布”。设成 2 后两个 Worker 各领一个 Reduce 任务，YARN UI 上能同时看到两个节点都有
任务记录。代价是输出被拆成 `part-r-00000`、`part-r-00001` 两个文件——这正是 `verify.sh` 必须合并
所有 `part-r-*` 再统计的原因。

小输入下某一个 Reduce 可能分不到数据，会产出空文件，这是正常现象，`verify.sh` 对此做了容错。

## 6. Driver 的退出码与安全检查

| 退出码 | 含义 | 触发条件 |
| --- | --- | --- |
| 0 | 成功 | 作业 `waitForCompletion` 返回 true |
| 1 | 作业失败 | Map/Reduce 任务失败，或集群不可用 |
| 2 | 参数或前置条件错误 | 参数个数不是 2，或输出目录已存在 |

输出目录已存在时在 Driver 里就拦住并返回 2，而不是交给 `FileOutputFormat` 抛异常。原因是我们
**不默认删除已有结果**：同一个 HDFS 路径上可能躺着别人上一轮的演示数据，误删代价比多敲一条
`hdfs dfs -rm -r` 大得多。

## 7. 三个脚本的设计

| 脚本 | 设计要点 |
| --- | --- |
| `build.sh` | 从 `.development` 读 `HADOOP_HOME`；类路径取 `hadoop classpath`（不用 Maven，镜像里没有）；每次全量重编，避免旧 class 混进 Jar；源文件用数组传递，路径含空格也不会被拆开 |
| `run.sh` | 路径不带协议头时自动补 `HDFS_URI`；先检查输入存在、输出不存在再提交；`-D` 参数放在两个路径前交给 `ToolRunner` 解析；`WORDCOUNT_LOCAL=1` 切到 `file:// + LocalJobRunner` 供上游未就绪时调试 |
| `verify.sh` | 先确认至少有一个 `part-r-*`（不把 `_SUCCESS` 当唯一证据），再合并全部 part 文件按单词累加，最后与预期逐词 diff；支持 `WORDCOUNT_EXPECTED` 指定其他数据集的预期 |

三个脚本都从 `BASH_SOURCE` 推导自身目录，再用 `../..` 找到项目根目录去读 `.development`，因此从任何
当前目录调用都有效，符合公共接口约定。

## 8. 与自带示例的对照

老师要求演示 Hadoop 自带 WordCount，本模块另外提供自研实现，两者定位不同：

| 对比项 | 自带示例 | 本模块 |
| --- | --- | --- |
| 分词 | `StringTokenizer`，按空白切，区分大小写 | 按非字母数字切，统一小写，保留中文与数字 |
| 代码可讲性 | 只有 Jar，看不到源码结构 | 四个类，逐层可讲 |
| 作用 | 证明集群环境正常 | 讲清 MapReduce 每一步，并承载本模块的测试与验收 |

两条链路的运行结果应当一致（对纯小写英文输入），这本身就是一次交叉验证。

## 9. 未完成与待补

- 真实集群上的 build / run / verify 实测记录：见 [test-results.md](test-results.md)
- 两个 Worker 的 Map/Reduce 任务分布截图：等 2—4 号集群就绪后补
- PPT 与视频：脚本见 [demo-script.md](demo-script.md)
