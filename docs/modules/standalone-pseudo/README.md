# 5 号：单机与伪分布式

## 1. 你要完成什么

交付两套可区分、可复现的运行方式：单机模式用本地文件执行 Hadoop 作业；伪分布式在一个节点里运行独立的 NameNode/DataNode 进程，完成 HDFS 操作。两者不能只展示“进入了 Docker”。

## 2. 在哪里改

| 位置 | 内容 |
| --- | --- |
| modes/standalone/ | 单机配置、运行入口、输入与说明 |
| modes/pseudo/ | 伪分布式配置、编排、服务启动与停止入口 |
| tests/standalone/、tests/pseudo/ | 两种模式各自的验证脚本 |
| 本目录 | 两模式对比、实验步骤、结果、截图、PPT/视频链接 |

模式专用配置放自己的目录，不改 3、4 号的完全分布式配置。仍使用原基础镜像；节点、卷、Compose 项目名和宿主机端口与完全分布式隔离。

## 3. 单机模式怎么做

1. 通过公共环境验证，在 feat/standalone-pseudo 开发。用原开发容器开始实现。
2. 在 modes/standalone/ 准备固定输入及独立配置：fs.defaultFS=file:///，mapreduce.framework.name=local；不启动 HDFS/YARN。
3. 编写运行入口，明确加载自己的配置，输出写到忽略的 runtime/ 下；不要依赖别人电脑已有的文件。
4. 先在开发容器运行下方官方示例了解流程，再把配置、输入和命令整理成你自己的可复现入口。
5. 添加结果核对和输出已存在时的失败检查；更新 modes/standalone/README.md。

以下是**现在可在公共开发容器内执行的单机练习**，使用未改动的基础配置；这不是你最终交付的脚本：

~~~bash
mkdir -p /workspace/runtime/standalone-demo/input
printf 'hello hadoop\nhello\n' > /workspace/runtime/standalone-demo/input/sample.txt
hadoop jar /opt/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar wordcount /workspace/runtime/standalone-demo/input /workspace/runtime/standalone-demo/output-001
cat /workspace/runtime/standalone-demo/output-001/part-r-*
~~~

预期 hadoop=1、hello=2，无 YARN application ID。重复执行换 output-002 等新目录。

## 4. 伪分布式怎么做

1. 在 modes/pseudo/ 新建专用 Compose 和配置。一个容器内运行 NameNode、DataNode；fs.defaultFS 指向该容器，副本数为 1，持久卷独立。
2. 先只打通 HDFS：首次显式格式化空目录，然后启动两个进程。使用本地守护进程命令，编写停止与退出处理；不照搬需要 SSH 的 start-dfs.sh。
3. 公共 hadoop-node.sh 的 master/worker 分别面向三节点组合，不能直接当作单容器伪分布式完整入口。可参考其初始化保护和进程清理，模式专用脚本放 modes/pseudo/。
4. 检查 jps 有 NameNode、DataNode，dfsadmin -report 有 1 个 Live DataNode。完成 mkdir、put、ls、cat；在自己的 Web 端口查看节点。
5. 配合单节点 HDFS，可先用本地 MapReduce 执行示例；若增加单节点 YARN，需显式配置并启动 ResourceManager/NodeManager，再验证 1 个 RUNNING 节点。说明里写清实际使用哪一种计算方式。
6. 重启自己的伪分布式环境，读回原文件；确认不影响完全分布式卷与端口。
7. 在 modes/pseudo/README.md 补上从电脑终端启动、进入、验证、重启、停止的完整命令。**目前这些入口尚待你实现，不要引用不存在的脚本让其他人运行。**

建议宿主机 Web 端口使用 19870（NameNode）、如启用 YARN 则用 18088，并在自己的编排和说明中一致记录，绑定 127.0.0.1。

## 5. 怎样算完成

- 单机：固定本地输入 → Hadoop 作业 → 正确本地输出，不连接三节点。
- 伪分布式：单节点 HDFS 注册、文件读写、独立持久化和重启验证通过。
- 两套入口、测试和说明都能由他人复现，清楚区分文件系统、进程数、节点数与计算方式。
- PPT/视频分别演示两套配置和结果，再对比完全分布式；本目录记录命令、截图及材料链接。
- 按 [协作规则](../../contributing.md) 提 PR 到 main。

参考：[Hadoop 官方单节点说明](https://hadoop.apache.org/docs/r3.3.6/hadoop-project-dist/hadoop-common/SingleCluster.html)。
