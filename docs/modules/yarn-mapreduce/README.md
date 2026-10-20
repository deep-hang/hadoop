# 4 号：YARN / MapReduce 分布式计算

## 1. 你要完成什么

让 master 运行 ResourceManager，两个 worker 运行 NodeManager；用真正的 YARN 作业证明任务能完成，并记录两个 worker 的计算参与情况。

## 2. 在哪里改

- config/yarn/yarn-site.xml、mapred-site.xml（新建）：资源管理和 MapReduce 配置。
- tests/yarn-mapreduce/：节点注册、示例任务、结果和任务分布检查。
- config/yarn/README.md：配置含义、资源参数和运行方法；本目录放实验结果及 PPT/视频链接。
- 2 号接入编排；3 号提供 HDFS；不改他们的文件来维护第二套配置。

## 3. 按什么顺序做

1. 通过公共环境验证，在 feat/yarn-mapreduce 开发。阅读 [公共启动说明](../../cluster-startup.md)，参考 [已验证配置](../../../tests/common/fixtures/cluster/)。
2. yarn-site.xml 设置 ResourceManager 为 master、启用 mapreduce_shuffle；配置 NodeManager 内存/vcores 和调度器分配范围。
3. mapred-site.xml 设置 mapreduce.framework.name=yarn，并配置应用类路径、AM、Map、Reduce 内存和 JVM 堆。任务内存必须能装进节点资源；参考参数是最小验证样例，不是所有电脑的固定标准。
4. 把配置及所需 HADOOP_* 环境、JVM 参数交给 2 号挂载。等 HDFS 就绪后，确认两个 NodeManager 注册成功。
5. 先用 Hadoop 自带 WordCount JAR 打通作业链路；这是环境验证，不替代 6 号实现自己的 WordCount。
6. 多个输入文件产生多个输入分片，核对实际任务数和容器所在节点。只看到两个 NodeManager 在线，不代表两个 worker 都算过任务。
7. 保存 application ID、成功状态、结果、两个节点的任务证据，通知 6、7 号可开始真实集群联调。将检查整理到自己的 tests/ 目录。

## 4. 怎样验证

**前提：2 号正式集群已接入 3、4 号配置且服务就绪。** 按 [2 号说明](../distributed/README.md) 进入 master，以下均在 master 内执行：

~~~bash
yarn node -list
hdfs getconf -confKey fs.defaultFS
mkdir -p /tmp/yarn-demo
for n in 1 2 3 4 5 6 7 8; do printf 'hello hadoop\n' > /tmp/yarn-demo/part-$n.txt; done
hdfs dfs -mkdir -p /project/input/yarn-demo
hdfs dfs -put /tmp/yarn-demo/*.txt /project/input/yarn-demo
hadoop jar /opt/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar wordcount /project/input/yarn-demo /project/output/yarn-demo/run-001
hdfs dfs -cat '/project/output/yarn-demo/run-001/part-r-*'
yarn application -list -appStates ALL
~~~

预期两个 RUNNING 节点，任务有 application ID、最终成功，输出 hadoop=8、hello=8。重复演示换新输出目录；已有输入不用重复 put。

在电脑浏览器打开 http://localhost:8088 查看作业。两个 worker 的 /opt/hadoop/logs/userlogs 中可查对应 application 的任务日志；区分 ApplicationMaster 与 Map/Reduce 容器，记录实际运行任务的节点。若只用了一个 worker，检查分片数量、资源余量和调度，再调整演示输入。

## 5. 怎样算完成

两节点注册、真实 YARN 作业成功、正确输出、两个 worker 的计算证据均齐全；记录 Docker 资源、YARN 资源及任务内存的关系。

PPT/视频讲清 ResourceManager、NodeManager、ApplicationMaster、Map/Shuffle/Reduce，按“配置 → 注册 → 提交 → 状态 → 节点任务 → 结果”演示。补好本目录实测记录，按 [协作规则](../../contributing.md) 提 PR 到 main。

参考：[MapReduce 官方教程](https://hadoop.apache.org/docs/r3.3.6/hadoop-mapreduce-client/hadoop-mapreduce-client-core/MapReduceTutorial.html)。
