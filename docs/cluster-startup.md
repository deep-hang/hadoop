# 公共集群启动能力（2、3、4 号接入）

老师已接受 Docker。组员首次接入仍按 [Windows / Mac 使用说明](platform-setup.md)，提交、PR 和同步上游按 [协作规则](contributing.md)。

## 1. 已提供的公共能力

[scripts/hadoop-node.sh](../scripts/hadoop-node.sh) 直接启动本节点服务，不依赖 SSH。由 2 号在集群编排中调用：

| 动作 | 用途 |
| --- | --- |
| init-namenode | 显式初始化 NameNode；已有 VERSION 时跳过，目录非空但无 VERSION 时拒绝格式化 |
| master | 启动 NameNode + ResourceManager；未初始化时直接报错 |
| worker | 启动 DataNode + NodeManager，worker1、worker2 均使用此动作 |

服务以前台进程运行；一项服务退出会停止同节点另一项并让容器失败退出。Docker 停止容器时转发终止信号。正常启动与重启不会自动执行格式化。

脚本从挂载的仓库调用，原镜像继续可用，不需要重新下载镜像。Maven 仍未包含；Java 示例可使用现有 javac、jar 或 Hadoop 自带示例 JAR。

## 2. 2、3、4 号怎样使用

1. 2 号复用原镜像，设置 master、worker1、worker2 的 hostname / 网络，挂载仓库到 /workspace。
2. 3、4 号准备真实 HDFS/YARN 配置；2 号按文件挂到 /opt/hadoop/etc/hadoop，保留其余默认配置。数据路径与 .development 一致。
3. 2、3 号挂载独立持久卷到数据目录的父目录，并确保 hadoop 用户（UID 1000）可写。2 号先对 master 显式运行一次 init-namenode，再启动三个节点。
4. 各节点命令使用 bash /workspace/scripts/hadoop-node.sh，加表中 master 或 worker。不从 bootstrap 的 dev 容器直接执行这些动作。
5. 2、4 号根据机器资源设置服务堆内存、NodeManager 可用资源、任务内存和类路径；容器已启动不等于服务就绪，注册和真实作业都要验证。

## 3. 如何复验公共能力

在电脑终端的项目根目录执行（需要 Python 3、Docker Compose 和已导入镜像）：

```text
python tests/common/check-cluster.py
```

测试使用 [独立配置](../tests/common/fixtures/cluster/)，创建随机命名的三节点项目，不映射宿主机端口。验证初始化保护、两个 DataNode、两个 NodeManager、真实 YARN 示例结果、重启后结果保留及服务失败后的节点退出；退出时只清理自己创建的容器、网络、卷，记录保存在 runtime/ 下。

配置中的资源参数仅用于本次最小验证；Mac 和其他电脑仍需本机复验。这个测试不替代 2—4 号的正式集群交付，也不是 6 号的 WordCount 模块。

启动依据：[Hadoop 3.3.6 官方集群说明](https://hadoop.apache.org/docs/r3.3.6/hadoop-project-dist/hadoop-common/ClusterSetup.html)。
