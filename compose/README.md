# 编排交接

`bootstrap.yaml` 是 1 号维护的基础开发入口，只有 `dev` 服务。需要显式传入 `--env-file .development`。

2 号在独立文件（建议 `distributed.yaml`）中实现三节点编排，复用 `hadoop-base:v0.1`；节点及服务名固定为 `master`、`worker1`、`worker2`。3、4 号提供服务配置与启动需求，再由 2 号集成。不能把基础镜像中的空 `core-site.xml` 当成可用 HDFS 配置。

容器配置应保留 Hadoop 自带的默认配置文件；将模块提供的 site XML、workers 等具体文件挂到 `/opt/hadoop/etc/hadoop/` 下对应位置，或在模块派生镜像中复制文件，避免以一个不完整目录覆盖整个 Hadoop 配置目录。

公共层已提供 [无 SSH 启动脚本与复验](../docs/cluster-startup.md)；正式三节点编排、持久卷和服务配置仍由 2—4 号实现。集群端口映射应绑定 `127.0.0.1`；数据目录的属主需兼容基础镜像的 `hadoop` 用户（UID 1000）。

本模块测试放 [对应 tests/ 子目录](../tests/distributed/)；实验步骤、结果和交付链接放 [对应 docs/modules/ 子目录](../docs/modules/distributed/)。
## 二号任务：三节点骨架

当前 distributed.yaml 使用 sleep infinity 保持三个容器运行。
已验证容器、节点名称解析和数据卷；尚未启动 HDFS/YARN。

以下命令在电脑终端的项目根目录执行。

启动：

```text
docker compose --env-file .development -p hadoop-distributed -f compose/distributed.yaml up -d
```

查看状态：

```text
docker compose --env-file .development -p hadoop-distributed -f compose/distributed.yaml ps
```

进入 master（输入 exit 返回电脑终端）：

```text
docker compose --env-file .development -p hadoop-distributed -f compose/distributed.yaml exec master bash
```

查看日志（骨架阶段没有 Hadoop 服务日志）：

```text
docker compose --env-file .development -p hadoop-distributed -f compose/distributed.yaml logs --tail 100
```

重启：

```text
docker compose --env-file .development -p hadoop-distributed -f compose/distributed.yaml restart
```

停止并保留数据卷：

```text
docker compose --env-file .development -p hadoop-distributed -f compose/distributed.yaml down
```

普通停止不加 --volumes。

Windows 骨架检查：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\distributed\check-skeleton.ps1
```

预期输出 SKELETON_CHECK_PASS，退出码为 0。
容器重建后的数据保留结果见 docs/modules/distributed/skeleton-results.md。
## 正式三节点编排与联合验证

distributed.yaml 已改为通过公共 hadoop-node.sh 启动真实 Hadoop 服务。
前面的 sleep infinity 骨架说明为历史阶段，不再描述当前配置。

运行前必须具备以下配套文件：

- config/hdfs/core-site.xml
- config/hdfs/hdfs-site.xml
- config/yarn/yarn-site.xml
- config/yarn/mapred-site.xml

以下命令在电脑终端的项目根目录执行。
本次联调使用 hadoop-distributed-recovery 项目名：

```text
docker compose --env-file .development -p hadoop-distributed-recovery -f compose/distributed.yaml config --quiet
```

仅首次初始化新环境：

```text
docker compose --env-file .development -p hadoop-distributed-recovery -f compose/distributed.yaml run --rm --no-deps master bash /workspace/scripts/hadoop-node.sh init-namenode
```

启动、检查和进入 master：

```text
docker compose --env-file .development -p hadoop-distributed-recovery -f compose/distributed.yaml up -d
docker compose --env-file .development -p hadoop-distributed-recovery -f compose/distributed.yaml ps -a
docker compose --env-file .development -p hadoop-distributed-recovery -f compose/distributed.yaml exec master bash
```

查看日志、重启、停止：

```text
docker compose --env-file .development -p hadoop-distributed-recovery -f compose/distributed.yaml logs --tail 100
docker compose --env-file .development -p hadoop-distributed-recovery -f compose/distributed.yaml restart
docker compose --env-file .development -p hadoop-distributed-recovery -f compose/distributed.yaml down
```

普通启动和重启不重新初始化，普通停止不加 --volumes。
容器 Up 不代表服务就绪，需确认两个 DataNode、两个 RUNNING
NodeManager，以及 HDFS 安全模式为 OFF。

Web 页面：http://localhost:9870 和 http://localhost:8088。

Compose 项目名决定网络和数据卷的隔离。后续命令必须使用同一项目名。
旧 hadoop-distributed 项目的故障数据卷仍保留，不要误用或删除。
不同项目使用相同宿主机端口时不能同时启动。

本次实测结果见 docs/modules/distributed/integration-results.md。