# 6 号：WordCount 单词统计

## 1. 你要完成什么

实现自己的 Java MapReduce 单词统计：输入文本 → Mapper 输出“单词、1” → 按单词汇总 → Reducer 输出次数。最终在真实 HDFS/YARN 上运行并展示两个 worker 的任务参与。

## 2. 在哪里改

- apps/wordcount/src/：Mapper、Reducer、Driver 源码。
- apps/wordcount/input/：可提交的小型固定输入；大规模演示数据用生成方法，不提交巨型文件。
- apps/wordcount/build.sh、run.sh、verify.sh（新建）：编译、执行、核对。
- tests/wordcount/：正常与失败用例；apps/wordcount/README.md 写实际操作入口。
- 本目录：实例规则、流程、实测结果、截图和 PPT/视频链接。

## 3. 按什么顺序做

1. 通过公共环境验证，在 feat/wordcount 开发；先读 [应用接口](../../interfaces.md)。
2. 先固定分词规则：是否区分大小写、标点如何处理、空行是否忽略。写进模块 README，让输入、预期结果和代码一致。
3. 编写 Mapper、Reducer、Driver：Driver 接收输入和输出参数，设置各阶段类型与输入/输出路径；作业失败时返回非零。
4. 写 build.sh：用现有 javac、jar 编译打包到 apps/wordcount/build/，编译类路径从 hadoop classpath 获取。基础镜像没有 Maven。脚本自行定位目录，从其他当前目录调用也应有效。
5. 写 run.sh <input> <output> 与 verify.sh <output>。最终按 HDFS 路径解释；输出目录已存在则失败，不自动删数据。verify 核对实际内容，不能只检查 _SUCCESS 存在。
6. 上游未就绪时，在开发容器先完成编译、分词/汇总逻辑和固定预期；需要临时本地模式调试时写清调用方式，不把本地成功当作 YARN 成功。
7. 等 2—4 号通知集群就绪，按 [协作规则](../../contributing.md) 同步 main，进入 master 后完成下方流程。
8. 再扩大输入分片，记录两个 worker 的 Map/Reduce 任务证据；与 4 号一起处理调度和资源问题。

## 4. 固定输入与预期

建议先使用这两个文件：

~~~text
a.txt:
hello hadoop
hello

b.txt:
hadoop world
~~~

预期词频 hadoop=2、hello=2、world=1。verify.sh 读取全部 part-r-*，按词频比较，不依赖文件排列顺序。另测空行、约定的大小写/标点、输入不存在、输出已存在。

## 5. 脚本实现后怎样跑

**以下要求你的三个脚本已实现，且正式三节点就绪。** 从电脑终端按 [2 号说明](../distributed/README.md) 进入 master，以下在容器内逐条执行：

~~~bash
bash /workspace/apps/wordcount/build.sh
hdfs dfs -mkdir -p /project/input/wordcount
hdfs dfs -put /workspace/apps/wordcount/input/*.txt /project/input/wordcount
bash /workspace/apps/wordcount/run.sh /project/input/wordcount /project/output/wordcount/run-001
bash /workspace/apps/wordcount/verify.sh /project/output/wordcount/run-001
hdfs dfs -cat '/project/output/wordcount/run-001/part-r-*'
~~~

第一次运行先使用固定小输入。重复演示输入不用重复 put，输出换 run-002。大规模测试使用独立输入子目录，verify 的预期要与该组数据匹配。

## 6. 怎样算完成

build、run、verify 成功与失败的退出码正确；小输入词频准确；真实 YARN application 成功，两个 worker 的计算参与有证据，不能仅截图节点在线。

PPT/视频讲清输入、Mapper、Shuffle、Reducer、Driver，再演示编译 → HDFS 输入 → 作业 → 节点任务 → 输出核对。本目录补真实命令与结果，按 [协作规则](../../contributing.md) 提 PR 到 main。

参考：[MapReduce 官方教程](https://hadoop.apache.org/docs/r3.3.6/hadoop-mapreduce-client/hadoop-mapreduce-client-core/MapReduceTutorial.html)。
