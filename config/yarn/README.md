# 4 号：YARN / MapReduce 配置

本目录只放 YARN 与 MapReduce 的站点配置，不含三节点编排（2 号 `compose/distributed.yaml`）和 HDFS 配置（3 号 `config/hdfs/`）。配置由 2 号**逐文件**挂载，不能用一个不完整的目录覆盖 `/opt/hadoop/etc/hadoop`。

## 1. 文件与挂载位置

| 本目录文件 | 挂载到三个节点 | 作用 |
| --- | --- | --- |
| `yarn-site.xml` | `/opt/hadoop/etc/hadoop/yarn-site.xml` | master 运行 ResourceManager；worker1、worker2 运行 NodeManager |
| `mapred-site.xml` | `/opt/hadoop/etc/hadoop/mapred-site.xml` | MapReduce 作业提交到 YARN，并规定 AM / Map / Reduce 资源 |

节点角色固定为 `.development` 中的 `MASTER_HOST=master`、`WORKER1_HOST=worker1`、`WORKER2_HOST=worker2`；服务由 [scripts/hadoop-node.sh](../../scripts/hadoop-node.sh) 在前台启动，不使用依赖 SSH 的 `start-yarn.sh`。

## 2. 先算资源，再写参数

本机实测 Docker Desktop 分配 **8 GB 内存 / 9 CPU**（Apple arm64，镜像为 `linux/amd64`，需要模拟运行）。按下面的账分配：

| 项目 | 数值 | 说明 |
| --- | --- | --- |
| master JVM | NameNode 512 MB + ResourceManager 512 MB 堆 | 两个常驻进程 |
| 每个 worker | NodeManager 2048 MB、2 vcores | 两个 worker 合计 4096 MB / 4 vcores |
| 单个 AM | 512 MB 容器，`-Xmx384m` | 跑在某个 worker 上 |
| 单个 Map / Reduce | 512 MB 容器，`-Xmx384m` | 每个节点最多 4 个 512 MB 容器 |
| 调度器范围 | 256–2048 MB | 容器请求不能超过单节点总量 |

约束关系：

```text
Docker 可用内存 ≥ master 堆 + Σ(NodeManager memory-mb) + JVM/OS 余量
AM、Map、Reduce 请求 ≤ yarn.scheduler.maximum-allocation-mb ≤ NodeManager memory-mb
同时运行的容器内存 ≤ NodeManager memory-mb
```

8 个输入文件会产生 8 个 Map 任务。每个节点可放 4 个 512 MB 容器（2048/512），两个节点合计 8 个；vcores 配置为 2，默认 CapacityScheduler 主要按内存计算，所以实际并发可能达到 4 个容器。作业还会启动 1 个 AM 和 2 个 Reduce，任务会分批完成。**只看到两个 NodeManager 在线不算通过**，必须看到两个 worker 的容器日志。

## 3. `yarn-site.xml` 参数

| 参数 | 值 | 原因 |
| --- | --- | --- |
| `yarn.resourcemanager.hostname` | `master` | RM 固定跑在 master；地址、调度器、Web 端口都由它派生 |
| `yarn.nodemanager.aux-services` | `mapreduce_shuffle` | Reduce 拉取 Map 输出必需的 Shuffle 服务 |
| `yarn.nodemanager.aux-services.mapreduce_shuffle.class` | `org.apache.hadoop.mapred.ShuffleHandler` | 与上一项配套的实现类 |
| `yarn.nodemanager.resource.memory-mb` | `2048` | 单节点可分配内存；两个 worker 共 4096 MB |
| `yarn.nodemanager.resource.cpu-vcores` | `2` | 单节点并发容器上限 |
| `yarn.scheduler.minimum-allocation-mb` | `256` | 最小容器单位 |
| `yarn.scheduler.maximum-allocation-mb` | `2048` | 不超过单节点内存 |
| `yarn.scheduler.minimum-allocation-vcores` | `1` | 每个容器至少 1 核 |
| `yarn.scheduler.maximum-allocation-vcores` | `2` | 不超过单节点 vcores |
| `yarn.nodemanager.vmem-check-enabled` | `false` | ARM 模拟 amd64 时虚拟内存统计偏差大，避免容器被误杀 |
| `yarn.nodemanager.env-whitelist` | 见文件 | 不把 `HADOOP_MAPRED_HOME` 等变量传进容器，任务会找不到 MapReduce 依赖 |

## 4. `mapred-site.xml` 参数

| 参数 | 值 | 原因 |
| --- | --- | --- |
| `mapreduce.framework.name` | `yarn` | 关键项；缺省会在本地运行，不能作为分布式证据 |
| `mapreduce.application.classpath` | common/hdfs/yarn/mapreduce 及其 `lib/*` | 精简镜像中显式给出 AM 和任务容器类路径 |
| `yarn.app.mapreduce.am.resource.mb` | `512` | AM 容器内存 |
| `yarn.app.mapreduce.am.command-opts` | `-Xmx384m` | AM 堆小于容器内存，留出 JVM 开销 |
| `mapreduce.map.memory.mb` | `512` | Map 容器内存 |
| `mapreduce.map.java.opts` | `-Xmx384m` | Map 堆 |
| `mapreduce.reduce.memory.mb` | `512` | Reduce 容器内存 |
| `mapreduce.reduce.java.opts` | `-Xmx384m` | Reduce 堆 |
| `mapreduce.client.submit.file.replication` | `2` | 两个 DataNode 时副本数取 2，避免默认 10 的等待和告警 |

## 5. 交给 2 号集成的内容

三个节点都需要：

1. 逐文件挂载 `config/yarn/yarn-site.xml`、`config/yarn/mapred-site.xml`（建议 `:ro`）。
2. 使用 `--env-file .development`，并保留 `HADOOP_COMMON_HOME`、`HADOOP_HDFS_HOME`、`HADOOP_YARN_HOME`、`HADOOP_MAPRED_HOME` 都指向 `/opt/hadoop`。
3. 设置 JVM 堆参数，避免默认值撑爆 8 GB：

   ```text
   HDFS_NAMENODE_OPTS=-Xmx512m
   HDFS_DATANODE_OPTS=-Xmx256m
   YARN_RESOURCEMANAGER_OPTS=-Xmx512m
   YARN_NODEMANAGER_OPTS=-Xmx256m
   ```

4. master 映射 `127.0.0.1:8088:8088`（YARN Web UI）；`9870` 由 HDFS 负责。
5. 三个节点使用同一网络，hostname 分别为 `master`、`worker1`、`worker2`；数据卷各自独立。
6. 启动后先确认 `yarn node -list` 出现两个 `RUNNING`，再提交应用。

参考片段（正式文件仍由 2 号维护）：

```yaml
volumes:
  - ../config/yarn/yarn-site.xml:/opt/hadoop/etc/hadoop/yarn-site.xml:ro
  - ../config/yarn/mapred-site.xml:/opt/hadoop/etc/hadoop/mapred-site.xml:ro
```

## 6. 怎样验证

### 6.1 自动检查（推荐）

在电脑终端、项目根目录执行，默认使用 2 号的 `compose/distributed.yaml` 和项目名 `hadoop-distributed`：

```bash
python3 tests/yarn-mapreduce/check-yarn.py
```

检查内容：两个 NodeManager 为 `RUNNING`；固定输入上传 HDFS；官方 WordCount 产生真实 application ID 且 `SUCCEEDED`；输出 `hadoop=8000`、`hello=8000`；worker1、worker2 均有非 AM 容器日志。任何一项失败返回非零，证据写入 `runtime/yarn-check-<时间>/`。

### 6.2 手工命令（在 master 内）

```bash
yarn node -list
hdfs dfsadmin -report
mkdir -p /tmp/yarn-demo
for n in 01 02 03 04 05 06 07 08; do
  awk 'BEGIN { for (i = 0; i < 1000; i++) print "hello hadoop" }' \
    > "/tmp/yarn-demo/part-$n.txt"
done
hdfs dfs -mkdir -p /project/input/yarn-check
hdfs dfs -put /tmp/yarn-demo/part-*.txt /project/input/yarn-check
hadoop jar /opt/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar \
  wordcount -D mapreduce.job.reduces=2 \
  /project/input/yarn-check /project/output/yarn-check/run-001
yarn application -status <application_id>
hdfs dfs -cat '/project/output/yarn-check/run-001/part-r-*'
```

预期输出合计 `hadoop 8000`、`hello 8000`。重复演示换新的输出目录；输出已存在时作业会失败，这是预期行为，不要用 `rm -r` 掩盖。

### 6.3 两个 worker 的计算证据

作业结束后，在电脑终端执行（compose 命令按 2 号的说明替换）：

```bash
docker compose --env-file .development -p hadoop-distributed \
  -f compose/distributed.yaml exec worker1 \
  find /opt/hadoop/logs/userlogs/<application_id> -mindepth 1 -maxdepth 1 -type d
docker compose --env-file .development -p hadoop-distributed \
  -f compose/distributed.yaml exec worker2 \
  find /opt/hadoop/logs/userlogs/<application_id> -mindepth 1 -maxdepth 1 -type d
```

两边都应有 `container_*` 目录；`_01_000001` 是 ApplicationMaster，**不能只拿它当两个 worker 都算过的证据**。其余 `_01_000002` 起为 Map/Reduce 容器。

## 7. 常见问题

| 现象 | 先检查 |
| --- | --- |
| `yarn node -list` 为 0 | 三个节点是否都挂载了 `yarn-site.xml`；RM hostname 是否为 `master`；NodeManager 日志 `/opt/hadoop/logs/yarn-*-nodemanager-*.log` |
| 作业一直 `ACCEPTED` | `yarn node -list -showDetails` 余量；AM/Map/Reduce 内存是否超过 2048 MB；是否两个节点都注册 |
| 容器被 KILLED | 降低 `-Xmx`；确认 512 MB 容器能装下堆；查看 worker 的 `userlogs/<app>/<container>/syslog` |
| `ClassNotFoundException` / 找不到 MapReduce 类 | `mapreduce.application.classpath` 是否包含 common/hdfs/yarn/mapreduce；`env-whitelist` 是否包含 `HADOOP_MAPRED_HOME` |
| Reduce 卡在 shuffle | `aux-services` 是否为 `mapreduce_shuffle`；两个 worker 是否能互通 8042/随机端口 |
| 只有一个 worker 有任务 | 输入分片是否足够（本目录用 8 个文件、2 个 Reduce）；单节点是否被 AM 占满；调度器是否把容器集中到一个节点 |
| 8088 打不开 | 2 号是否映射 `127.0.0.1:8088:8088`；RM 是否真正启动 |

## 8. 当前限制与实测状态

- 2026-10-27 本机预验证通过：`application_1793080038565_0001` 成功，输出 `hadoop=8000`、`hello=8000`，worker1/worker2 分别有 6/4 个任务容器。使用 `runtime/yarn-lab/` 的临时编排和公共 HDFS fixture，因为 2 号 `compose/distributed.yaml`、3 号 `config/hdfs/` 尚未合入。正式集群就绪后必须重跑 `check-yarn.py`，用正式 application ID 替换预验证记录。
- Apple Silicon 必须在 Docker Desktop 启用 Rosetta（`useVirtualizationFrameworkRosetta=true`）。未启用时 ResourceManager 在 QEMU 模拟下超过 10 分钟仍未启动；启用后约 2 分钟内完成注册。该设置属于本机 Docker，不是仓库配置。
- 未启用 JobHistory Server 和日志聚合；不要依赖 `yarn logs`，按上面的 userlogs 路径取证。
- 资源参数按 8 GB Docker 虚拟机设定。换机器时同时调整 NodeManager 内存、调度器上限和任务内存，不能只改一项。

相关文档：[模块指南](../../docs/modules/yarn-mapreduce/README.md) · [公共接口](../../docs/interfaces.md) · [集群启动](../../docs/cluster-startup.md)
