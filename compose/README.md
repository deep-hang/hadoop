# 三节点编排使用说明

bootstrap.yaml 是公共开发容器入口。
distributed.yaml 是正式三节点 Hadoop 编排，使用 hadoop-base:v0.1。

## 服务与配置

- master：NameNode、ResourceManager。
- worker1、worker2：各运行 DataNode、NodeManager。
- 使用公共 scripts/hadoop-node.sh，不依赖 SSH。
- 仓库读写挂载到 /workspace。
- 三个节点分别使用独立命名卷，挂载到 /var/lib/hadoop。
- 四份 XML 逐文件只读挂载，保留 Hadoop 其余默认配置。

运行前必须具备以下配套文件：

- config/hdfs/core-site.xml
- config/hdfs/hdfs-site.xml
- config/yarn/yarn-site.xml
- config/yarn/mapred-site.xml

历史骨架验证见 ../docs/modules/distributed/skeleton-results.md。
当前编排启动真实 Hadoop 服务。

## 项目名与数据保留

下面命令在电脑终端的项目根目录执行，统一使用项目名
`hadoop-distributed-recovery`。Windows 使用 PowerShell；Mac 使用终端，
除下面的环境变量设置外，Docker 命令相同。

数据卷保存在各自电脑上，不会随 Git 下载：
- **新成员首次使用**：本机没有此项目的数据，需要执行下面的首次初始化步骤。
- **已用此项目初始化并运行过**：继续使用本机已有的数据卷，正常启动时跳过初始化。
- **2 号原来的故障环境**：旧 `hadoop-distributed` 项目的卷保留；新环境用 recovery 项目，不切回旧项目。

Compose 项目名决定默认网络和命名卷的隔离。
同一套数据必须始终使用相同项目名。

## 可调整的网页访问端口

| 环境变量 | 默认电脑端口 | 容器端口 |
| --- | --- | --- |
| HDFS_WEB_HOST_PORT | 9870 | 9870 |
| YARN_WEB_HOST_PORT | 8088 | 8088 |

端口只绑定 127.0.0.1。

如果 Windows 保留了 9870，或该端口已被其他程序占用，
在执行 Compose 命令前设置：

```powershell
$env:HDFS_WEB_HOST_PORT = "19870"
```

如果还需调整 YARN 网页端口：

```powershell
$env:YARN_WEB_HOST_PORT = "18088"
```

设置后，网页地址分别为：
http://localhost:19870 和 http://localhost:18088。

没有设置变量时，使用：
http://localhost:9870 和 http://localhost:8088。

这些变量只作用于当前 PowerShell 会话。
新开终端后需要重新设置；不修改 Hadoop XML 或公共 .development。
Mac/Linux 可使用 export HDFS_WEB_HOST_PORT=19870 设置对应变量。

修改映射后执行 up -d 使配置生效，仅执行 restart 不会更新端口映射。
up -d 可能重建 master 容器，应在没有运行中作业时操作，数据卷保留。
选用的宿主机端口也必须未被占用或保留。

## 检查配置

```powershell
docker compose --env-file .development -p hadoop-distributed-recovery -f compose/distributed.yaml config --quiet
```

## 仅首次初始化全新环境

新成员第一次在本机运行此项目时执行一次。已有正常初始化数据的成员跳过此步；
不要根据别人的电脑已经运行过，就跳过自己电脑的首次初始化。

```powershell
docker compose --env-file .development -p hadoop-distributed-recovery -f compose/distributed.yaml run --rm --no-deps master bash /workspace/scripts/hadoop-node.sh init-namenode
```

普通启动、停止和重启不重新格式化。

## 启动、查看和进入

```powershell
docker compose --env-file .development -p hadoop-distributed-recovery -f compose/distributed.yaml up -d
docker compose --env-file .development -p hadoop-distributed-recovery -f compose/distributed.yaml ps -a
docker compose --env-file .development -p hadoop-distributed-recovery -f compose/distributed.yaml exec master bash
```

在容器内输入 exit 返回电脑终端。

## 服务就绪检查

以下仍在电脑终端执行：

```powershell
docker compose --env-file .development -p hadoop-distributed-recovery -f compose/distributed.yaml exec -T master hdfs dfsadmin -report
docker compose --env-file .development -p hadoop-distributed-recovery -f compose/distributed.yaml exec -T master hdfs dfsadmin -safemode get
docker compose --env-file .development -p hadoop-distributed-recovery -f compose/distributed.yaml exec -T master yarn node -list
```

应有两个 Live DataNode、安全模式 OFF、两个 RUNNING NodeManager。
容器 Up 不等于 Hadoop 已就绪；未就绪时等待后复查，失败时查看日志。

## 运行模块测试

保持在电脑终端、项目根目录，使用同一个项目名。需要已接入 3、4 号的测试代码。

Windows 的三节点名称、网络和卷权限检查：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ./tests/distributed/check-skeleton.ps1 -Project hadoop-distributed-recovery
```

HDFS 检查（Windows / Mac）：

```text
docker compose --env-file .development -p hadoop-distributed-recovery -f compose/distributed.yaml exec -T master bash /workspace/tests/hdfs/run-all.sh
```

YARN 真实计算检查（Windows）：

```powershell
python tests/yarn-mapreduce/check-yarn.py --project hadoop-distributed-recovery
```

Mac 将 `python` 换成 `python3`。请保留 `--project` 参数，4 号脚本的默认项目名不同；
省略后会查找另一个集群，可能报找不到容器。
三项分别应输出 `SKELETON_CHECK_PASS`、`HDFS_TEST_PASS` 和 YARN 的 `PASS`，退出码为 0。
名称、网络检查不代替 HDFS/YARN 测试；失败时先检查项目名、服务状态和日志。

## 日志、重启与停止

```powershell
docker compose --env-file .development -p hadoop-distributed-recovery -f compose/distributed.yaml logs --tail 100
docker compose --env-file .development -p hadoop-distributed-recovery -f compose/distributed.yaml restart
docker compose --env-file .development -p hadoop-distributed-recovery -f compose/distributed.yaml down
```

普通停止不加 --volumes，不删除旧卷，也不靠重新格式化排错。

## 实验证据

HDFS 读写、双副本、容器重建后数据保留及真实 YARN 作业结果，
见 ../docs/modules/distributed/integration-results.md。
