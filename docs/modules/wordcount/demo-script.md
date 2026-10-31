# WordCount 演示脚本（PPT + 视频）

负责人：6 号。对应任务书要求：PPT 12 项内容 + 视频完整演示“编译 → HDFS 输入 → 作业 → 节点任务 → 输出核对”。

以下内容按**实际可执行的顺序**写，录屏时照着念、照着敲即可。

## 1. PPT 结构（12 页，对应任务书 9.7 的 12 项）

| 页 | 标题 | 要点 | 配图建议 |
| --- | --- | --- | --- |
| 1 | WordCount 实例目的 | MapReduce 最小完整闭环；同时验证数据分布与计算分布；本实例验收标准是“结果正确 + 两个 Worker 都参与” | 一张“输入→Mapper→Shuffle→Reducer→输出”的总流程图 |
| 2 | 输入数据设计 | 两个文件 a.txt / b.txt；单词跨文件交叉出现，才能看出 Shuffle 的作用；预期 hadoop=2 hello=2 world=1 | 两个输入文件的截图 + 预期词频表 |
| 3 | Mapper | 按行读入，`Tokenizer` 切词，输出 `(单词,1)`；分词三条规则（字母数字成词、其余字符分隔、统一小写） | Mapper 代码 3 行核心 + 一行输入输出示例 |
| 4 | Shuffle | 按单词分区、排序、分组；同名单词必到同一 Reduce；`hadoop` 来自两个 Map 任务合并成 2 | Map 输出 → 分区 → Reduce 输入的箭头图，用 hadoop 举例 |
| 5 | Reducer | 累加所有 1；同时注册为 Combiner，Map 端先局部合并减少传输 | Reducer reduce() 代码 + Combiner 前后数据量对比 |
| 6 | Driver | 校验参数、检查输出目录不存在、设置各阶段类型、提交并等待；退出码 0/1/2 | Driver 主要配置片段 + 退出码表 |
| 7 | 实例配置 | 编译用镜像自带 javac/jar（无 Maven）；类路径取 `hadoop classpath`；产物 build/wordcount.jar；Reduce 数设 2 的理由 | build.sh 关键行 + 为什么 2 个 Reduce |
| 8 | Build 过程 | `bash build.sh` 的两个阶段（javac → jar），成功输出 BUILD PASS | 终端截图 |
| 9 | HDFS 输入 | `hdfs dfs -mkdir -p` / `-put` / `-ls`，输入放在 /project/input/wordcount | HDFS ls 结果截图，显示两个文件和副本数 |
| 10 | MapReduce 执行 | 提交命令、application id、Map 任务数=分片数、Reduce 任务数=2、tracking URL | YARN UI 作业页截图 |
| 11 | 多 Worker 计算情况 | 逐个 Attempt 所在节点，worker1 与 worker2 都出现；`part-r-*` 两个文件 | YARN UI 任务 Attempt 列表截图（重点！） |
| 12 | 最终结果 | verify.sh 输出 VERIFY PASS + 词频表；与自带示例结果对照一致 | 终端 verify 输出截图 |

## 2. 视频录制顺序

一段连续录屏最省事，顺序与命令严格对应：

```text
① 说明当前环境
   docker ps                    # 三个节点在跑：master / worker1 / worker2

② 编译（对应 PPT 第 7、8 页）
   bash /workspace/apps/wordcount/build.sh
   ls -l /workspace/apps/wordcount/build/wordcount.jar

③ 上传输入到 HDFS（第 9 页）
   hdfs dfs -mkdir -p /project/input/wordcount
   hdfs dfs -put /workspace/apps/wordcount/input/*.txt /project/input/wordcount
   hdfs dfs -ls /project/input/wordcount

④ 提交作业（第 10 页）
   bash /workspace/apps/wordcount/run.sh /project/input/wordcount /project/output/wordcount/run-001
   # 记下打印出来的 application id 与 tracking URL

⑤ 看 YARN 上的任务分布（第 11 页，本实例的重点）
   浏览器打开 http://localhost:8088
   进入刚提交的 application -> 看 Map/Reduce 任务数 -> 点开每个 Attempt 看所在节点
   要求：worker1 与 worker2 都出现

⑥ 核对结果（第 12 页）
   bash /workspace/apps/wordcount/verify.sh /project/output/wordcount/run-001
   hdfs dfs -cat '/project/output/wordcount/run-001/part-r-*'

⑦ 规模放大（可选，但要录）
   bash /workspace/tests/wordcount/check-large.sh 5 2000
   # Map 任务数随分片增加，两个 Worker 的分工更明显

⑧ 失败演示（体现严谨性，30 秒）
   bash /workspace/apps/wordcount/run.sh /project/input/wordcount /project/output/wordcount/run-001
   # 输出已存在 -> 明确失败，不覆盖旧结果
```

## 3. 讲解稿（可直接照念）

### 开场（30 秒）

> 我负责的是 WordCount 实例。这个实例在 MapReduce 里相当于“冒烟测试”，但它不只是跑个 Hello World：
> 我们要证明两件事——结果算对了，以及两个 Worker 真的都参与了计算。整个流程是编译、上传到 HDFS、
> 提交作业、核对输出，四个环节都可复现。

### 讲 Mapper（30 秒）

> Mapper 拿到的是“一行文本”。我们先把分词规则固定下来，规则只有三条：连续的字母数字算一个单词，
> 其他字符都是分隔符，统一转小写。所以 `Hello`、`HELLO`、`hello` 是同一个词。切完每个单词输出
> 一个键值对，键是单词，值是 1。

### 讲 Shuffle（40 秒，重点）

> Shuffle 是整个 MapReduce 里最容易被忽略、但最关键的一步。我们的 `hadoop` 这个词在 a.txt 和 b.txt
> 里各出现一次，分别在两个不同的 Map 任务里。Shuffle 按单词分区，保证同一个单词一定送到同一个
> Reduce 任务，所以最后能合并成 2，而不是输出两行 `hadoop 1`。这就是 Shuffle 存在的意义。

### 讲 Reducer 与 Combiner（30 秒）

> Reducer 就是把同一个单词收到的所有 1 加起来。我们把 Reducer 同时注册成 Combiner，让它在 Map 端
> 先做一次局部合并。因为加法满足结合律，Combiner 不会改变结果，但能让 Shuffle 传输的数据量从
> “每个单词一条”降到“每个 Map 每个单词一条”。

### 讲 Reduce 数为什么设 2（30 秒）

> 一个 Reduce 任务只能跑在一个节点上。如果只设 1 个，所有 Reduce 计算都落在同一个 Worker 上，
> 所谓“计算分布”就只剩 Map 分布了。设成 2 个之后，两个 Worker 各领一个 Reduce 任务，YARN UI 上
> 能同时看到两个节点都有任务记录。代价是输出被拆成两个 part 文件，所以核对脚本必须合并所有
> `part-r-*` 再统计。

### 讲核对（30 秒）

> 核对不是看 `_SUCCESS` 存在就算通过，那只能说明作业正常结束，说明不了结果对不对。脚本会把所有
> part 文件读出来，按单词累加，和预期逐词比对：多一个词、少一个词、次数不对，都算失败。

### 讲结论（20 秒）

> 最终结果 hadoop 2 次、hello 2 次、world 1 次，与预期完全一致；YARN 上 Map 和 Reduce 任务分别
> 落在 worker1 和 worker2，两个 Worker 都参与了计算。这条链路从仓库里任意一台机器都能复现。

## 4. 截图清单（录制后统一保存）

放在 `docs/modules/wordcount/screenshots/`，命名按顺序：

| 文件名 | 内容 |
| --- | --- |
| 01-build.png | build.sh 输出 BUILD PASS |
| 02-hdfs-put.png | 输入文件已上传到 HDFS |
| 03-yarn-app.png | YARN UI 上该 application 的概览（任务数、状态） |
| 04-yarn-nodes.png | Map/Reduce Attempt 所在节点，worker1 + worker2 都在 |
| 05-verify.png | verify.sh 输出 VERIFY PASS 与词频表 |
| 06-result.png | `hdfs dfs -cat part-r-*` 的实际内容 |
| 07-fail-exists.png | 输出已存在时明确失败 |
