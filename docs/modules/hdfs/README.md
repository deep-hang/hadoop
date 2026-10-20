# 3 号：HDFS 分布式存储

## 1. 你要完成什么

让 master 的 NameNode 管理两个 worker 的 DataNode，证明文件能上传、读取，数据块和副本确实在两个 worker 上，重启不丢文件。

## 2. 在哪里改

- config/hdfs/core-site.xml、hdfs-site.xml（新建）：HDFS 地址、数据目录、副本配置。
- tests/hdfs/：固定测试输入与读写、副本、重启验证。
- config/hdfs/README.md：配置含义和实际入口；本目录记录结果、截图、PPT、视频链接。
- Compose 挂载和卷由 2 号接入；不要直接改他的编排文件。

## 3. 按什么顺序做

1. 通过公共环境验证，在 feat/hdfs 开发。先看 [公共接口](../../interfaces.md) 和 [HDFS 测试配置](../../../tests/common/fixtures/cluster/hdfs-site.xml)。
2. 写 core-site.xml：fs.defaultFS 固定为 hdfs://master:9000。写 hdfs-site.xml：dfs.namenode.name.dir 为 /var/lib/hadoop/hdfs/namenode，dfs.datanode.data.dir 为 /var/lib/hadoop/hdfs/datanode，两个 worker 的实验副本数设为 2。
3. 把配置含义和挂载清单交给 2 号。以他提供的正式集群为运行环境，检查数据卷可写；使用公共脚本显式初始化，不手工反复格式化。
4. 进入 master，检查实际加载的配置和两个 DataNode 注册情况。
5. 准备固定输入，依次完成 mkdir、put、ls、cat 和内容核对，尽早通知 6、7 号存储已可用。
6. 再用 fsck 查看块位置，保存 worker1、worker2 的证据；配合 2 号重启，确认文件仍可读。
7. 把这些步骤写进 tests/hdfs/ 的测试脚本；错误、内容不一致或节点数不符时返回非零。

## 4. 怎样验证

**先等 2 号交付正式集群并接入你的配置**，按 [2 号说明](../distributed/README.md) 从电脑终端进入 master。以下命令均在 master 内执行：

~~~bash
hdfs getconf -confKey fs.defaultFS
hdfs getconf -confKey dfs.namenode.name.dir
hdfs getconf -confKey dfs.datanode.data.dir
hdfs dfsadmin -report
mkdir -p /tmp/hdfs-demo
printf 'hello hadoop\n' > /tmp/hdfs-demo/sample.txt
hdfs dfs -mkdir -p /project/input/hdfs-demo
hdfs dfs -put /tmp/hdfs-demo/sample.txt /project/input/hdfs-demo/sample-001.txt
hdfs dfs -ls /project/input/hdfs-demo
hdfs dfs -cat /project/input/hdfs-demo/sample-001.txt
hdfs fsck /project/input/hdfs-demo/sample-001.txt -files -blocks -locations
~~~

预期地址与目录符合公共接口，Live datanodes 为 2，cat 输出 hello hadoop。fsck 应显示健康文件及两个副本位置；必要时配合 dfsadmin -report 对照节点名/IP。在电脑浏览器打开 http://localhost:9870 查看 Live Nodes。

再次演示请用 sample-002.txt 等新文件名，避免覆盖。重启前后各读取一次原文件并比较内容；重启命令由 2 号提供，不删卷。

## 5. 怎样算完成

两个 DataNode、文件读写、两节点副本位置、重启持久化均有实测证据。小文件也可展示副本，但若讲解“多个数据块”，要准备大于实际块大小的输入并核对块数。

PPT/视频讲清 NameNode、DataNode、Block、Replication，再演示配置 → 注册 → 上传读取 → 块位置 → 重启读取。本目录补实测命令、输出及材料链接，按 [协作规则](../../contributing.md) 提 PR 到 main。

参考：[HDFS 官方命令](https://hadoop.apache.org/docs/r3.3.6/hadoop-project-dist/hadoop-hdfs/HDFSCommands.html)。
