# 编排交接

`bootstrap.yaml` 是 1 号维护的基础开发入口，只有 `dev` 服务。需要显式传入 `--env-file .development`。

2 号在独立文件（建议 `distributed.yaml`）中实现三节点编排，复用 `hadoop-base:v0.1`；节点及服务名固定为 `master`、`worker1`、`worker2`。3、4 号提供服务配置与启动需求，再由 2 号集成。不能把基础镜像中的空 `core-site.xml` 当成可用 HDFS 配置。

容器配置应保留 Hadoop 自带的默认配置文件；将模块提供的 site XML、workers 等具体文件挂到 `/opt/hadoop/etc/hadoop/` 下对应位置，或在模块派生镜像中复制文件，避免以一个不完整目录覆盖整个 Hadoop 配置目录。

Phase 0 不提供三节点网络、持久卷、格式化或守护进程脚本。集群端口映射应绑定 `127.0.0.1`；数据目录的属主需兼容基础镜像的 `hadoop` 用户（UID 1000）。
