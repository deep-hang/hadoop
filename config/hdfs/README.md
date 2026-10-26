# 3 号：HDFS 配置

本目录提供 HDFS 的两个配置文件，由 2 号接入 `compose/distributed.yaml`。端点、路径、副本数全部对齐 [`.development`](../../.development) 与 [公共接口](../../docs/interfaces.md)，不接受各节点各自手改。

**当前状态：配置已写好，尚未在真实三节点集群实测。** 需 2 号完成挂载与启动后，由 3 号在 master 内执行 [tests/hdfs/](../../tests/hdfs/) 的检查并回填结果。

## 1. 文件与取值

| 文件 | 挂载目标（容器内） | 作用 |
| --- | --- | --- |
| `core-site.xml` | `/opt/hadoop/etc/hadoop/core-site.xml` | HDFS 默认 URI、临时目录、IO 缓冲 |
| `hdfs-site.xml` | `/opt/hadoop/etc/hadoop/hdfs-site.xml` | 元数据/数据目录、副本数、安全模式、Web UI |

### core-site.xml

| 属性 | 值 | 为什么这么设 |
| --- | --- | --- |
| `fs.defaultFS` | `hdfs://master:9000` | 契约固定值。取 `HDFS_URI`，`master` 是容器网络内的服务名，9000 是 NameNode RPC 端口 |
| `hadoop.tmp.dir` | `/var/lib/hadoop/tmp` | 默认落在容器 `/tmp`，容器重建即丢；改到持久卷内，跟随卷保留 |
| `io.file.buffer.size` | `131072` | 官方集群配置建议 128 KB，默认 4 KB 偏小 |

### hdfs-site.xml

| 属性 | 值 | 为什么这么设 |
| --- | --- | --- |
| `dfs.namenode.name.dir` | `/var/lib/hadoop/hdfs/namenode` | 必须等于 `.development` 的 `HDFS_NAMENODE_DIR`。`scripts/hadoop-node.sh` 用 `hdfs getconf -confKey` 读取后与它比对，不一致直接 exit 1 |
| `dfs.datanode.data.dir` | `/var/lib/hadoop/hdfs/datanode` | 必须等于 `HDFS_DATANODE_DIR`，同上 |
| `dfs.replication` | `2` | 一个 Master + 两个 Worker 的拓扑下，每个块存 2 份，正好一个 Worker 一份 |
| `dfs.namenode.safemode.extension` | `0` | 报块完成即退出安全模式，演示时不必空等默认的 30 秒 |
| `dfs.namenode.http-address` | `0.0.0.0:9870` | 契约端口 9870；监听所有网卡，2 号映射宿主机端口后才能用浏览器访问 |

未设置的项一律使用 Hadoop 3.3.6 默认值：块大小 128 MB、`dfs.datanode.address` 0.0.0.0:9866、`dfs.permissions.enabled` true。

## 2. 交给 2 号的挂载清单

### 2.1 配置必须逐文件挂载

公共接口要求「逐文件接入实际 Hadoop 配置目录，不让一套配置覆盖另一套」，所以**不要**把整个 `config/hdfs/` 或整个 `config/` 目录挂到 `/opt/hadoop/etc/hadoop/`，那会盖掉 4 号的 YARN 配置和镜像自带的其余 conf。按下面逐条挂（路径相对 `compose/distributed.yaml` 所在的 `compose/` 目录）：

```yaml
  master:
    volumes:
      - ..:/workspace
      - ../config/hdfs/core-site.xml:/opt/hadoop/etc/hadoop/core-site.xml:ro
      - ../config/hdfs/hdfs-site.xml:/opt/hadoop/etc/hadoop/hdfs-site.xml:ro
      - ../config/yarn/yarn-site.xml:/opt/hadoop/etc/hadoop/yarn-site.xml:ro        # 4 号提供
      - ../config/yarn/mapred-site.xml:/opt/hadoop/etc/hadoop/mapred-site.xml:ro    # 4 号提供
      - master-data:/var/lib/hadoop
    ports:
      - "9870:9870"    # NameNode Web UI，只需 master 映射
      - "8088:8088"    # ResourceManager Web UI，4 号负责
  worker1:
    volumes:
      - ..:/workspace
      - ../config/hdfs/core-site.xml:/opt/hadoop/etc/hadoop/core-site.xml:ro
      - ../config/hdfs/hdfs-site.xml:/opt/hadoop/etc/hadoop/hdfs-site.xml:ro
      - ../config/yarn/yarn-site.xml:/opt/hadoop/etc/hadoop/yarn-site.xml:ro
      - ../config/yarn/mapred-site.xml:/opt/hadoop/etc/hadoop/mapred-site.xml:ro
      - worker1-data:/var/lib/hadoop
  worker2:
    volumes:
      - ..:/workspace
      - ../config/hdfs/core-site.xml:/opt/hadoop/etc/hadoop/core-site.xml:ro
      - ../config/hdfs/hdfs-site.xml:/opt/hadoop/etc/hadoop/hdfs-site.xml:ro
      - ../config/yarn/yarn-site.xml:/opt/hadoop/etc/hadoop/yarn-site.xml:ro
      - ../config/yarn/mapred-site.xml:/opt/hadoop/etc/hadoop/mapred-site.xml:ro
      - worker2-data:/var/lib/hadoop
```

### 2.2 卷与权限

| 要求 | 说明 |
| --- | --- |
| 卷挂载点 | 三个节点各自的命名卷 → `/var/lib/hadoop`（他骨架里已有，保持不变） |
| 属主 | 卷根目录必须 UID 1000（`hadoop`）可写，`hadoop-node.sh` 会检查 DataNode 目录可写 |
| 目录 | `hdfs/namenode`、`hdfs/datanode`、`tmp` 由脚本和 Hadoop 自行创建，不需要手工预建，也不要手工 `-format` |
| 端口 | 只需 master 映射 `9870`（4 号再加 `8088`）；9000、9866 走容器网络，不映射宿主机 |

### 2.3 启动顺序（沿用公共 `scripts/hadoop-node.sh`）

```text
# 首次，且 NameNode 目录为空时执行一次
docker compose --env-file .development -f compose/distributed.yaml \
  run --rm --no-deps master bash /workspace/scripts/hadoop-node.sh init-namenode

# 之后每次启动
docker compose --env-file .development -f compose/distributed.yaml up -d
```

各服务的 `command` 改为 `bash /workspace/scripts/hadoop-node.sh master`（master）与 `... worker`（worker1、worker2）；`env_file` 必须包含 `.development`，否则脚本读不到 `HDFS_NAMENODE_DIR`、`HDFS_DATANODE_DIR` 会直接失败。

`init-namenode` 自带保护：已有 `VERSION` 时跳过，目录非空但无 `VERSION` 时拒绝格式化。**不删卷重启不会重新格式化**，这是重启持久化验收的前提。

## 3. 配置生效后怎样自检

在 master 容器内执行（2 号交付集群后）：

```bash
hdfs getconf -confKey fs.defaultFS          # hdfs://master:9000
hdfs getconf -confKey dfs.namenode.name.dir # /var/lib/hadoop/hdfs/namenode
hdfs getconf -confKey dfs.datanode.data.dir # /var/lib/hadoop/hdfs/datanode
hdfs dfsadmin -report                       # Live datanodes (2)
```

或直接跑本模块的检查脚本（含上述项与读写、副本、重启验证）：

```bash
bash /workspace/tests/hdfs/run-all.sh
```

## 4. 常见失败

| 现象 | 原因 |
| --- | --- |
| `Configuration mismatch: dfs.namenode.name.dir=...` | XML 里的路径与 `.development` 不一致，或改了 `.development` 却没同步 XML |
| `Configuration mismatch` 显示空值 | XML 没挂进 `/opt/hadoop/etc/hadoop/`，`hdfs getconf` 读到的是镜像里的空 `core-site.xml` |
| `Live datanodes (0)` 或只有 1 个 | 卷不可写、worker 服务未启动、或 `data.dir` 指向容器内非卷路径 |
| 浏览器打不开 9870 | master 未映射端口，或 `dfs.namenode.http-address` 被绑到某张具体网卡 |
| 重启后文件消失 | 用了带 `--volumes` 的 `down`，卷被删除；正常停止不要删卷 |

模块测试脚本见 [tests/hdfs/](../../tests/hdfs/README.md)。实测记录、截图、PPT 与视频链接待集群打通后补在本节下方。
