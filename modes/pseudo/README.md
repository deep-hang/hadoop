# 5 号：伪分布式模式

已实现：一个容器内运行 NameNode、DataNode，使用 `hdfs://pseudo:9000` 存储数据，副本数为 1；计算使用本地 MapReduce。数据卷与三节点集群相互独立。

首次初始化、启动网页和运行示例，见 [两种模式使用说明](../../docs/modules/standalone-pseudo/README-RUNTIME.md)。自动测试见 [伪分布式测试](../../tests/pseudo/)。

伪分布式与三节点演示的网页端口可能都使用 19870；依次运行演示，或在启动伪分布式前设置 `M5_PSEUDO_WEB_PORT` 为其他可用端口。不要删除已有数据卷来解决端口问题。

本模块测试放 [对应 tests/ 子目录](../../tests/pseudo/)；实验步骤、结果和交付链接放 [对应 docs/modules/ 子目录](../../docs/modules/standalone-pseudo/)。
