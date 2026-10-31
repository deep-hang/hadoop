# HDFS 读写、副本与双 DataNode 测试

负责人：3 号。脚本已在本地写完并通过 `bash -n` 语法检查，**尚未在真实三节点集群实跑**——等 2 号的 `compose/distributed.yaml` 接上配置与 `hadoop-node.sh` 后，在 master 内执行并回填第 5 节的结果。

## 1. 前置条件

| 项 | 要求 |
| --- | --- |
| 集群 | 2 号的三节点集群已启动，master 上 NameNode 在跑，worker1/worker2 的 DataNode 已注册 |
| 配置 | `config/hdfs/` 的两个 XML 已挂到 `/opt/hadoop/etc/hadoop/` |
| 执行位置 | **master 容器内**（`hdfs` 命令与 `HADOOP_CONF_DIR` 都就绪的节点） |
| 数据卷 | 未删卷。`init-namenode` 只在空目录执行过，重启不重新格式化 |

## 2. 脚本清单

| 脚本 | 验证内容 | 失败条件 |
| --- | --- | --- |
| `check-config.sh` | `getconf` 读到的 `fs.defaultFS`、`name.dir`、`data.dir`、`replication` 是否等于契约值；数据目录是否在持久卷内 | 任一项不符即退出 1 |
| `check-datanodes.sh` | `dfsadmin -report` 中 Live DataNode 数为 2，且 hostname 含 worker1、worker2 | 数量不符或缺少某个 worker |
| `check-readwrite.sh` | `mkdir` → `put` → `ls` → `cat` → `get`，大小、副本数、内容逐字节比对 | 上传后找不到、大小/副本数不符、`cmp` 不一致 |
| `check-blocks.sh` | `fsck -files -blocks -locations`：状态 HEALTHY、缺块/欠副本/损坏为 0、每块 2 个副本且都落在 Live DataNode 上 | 非 HEALTHY、复制数不足、副本落在非 Live 节点、摘要字段一条都识别不出 |
| `check-persistence.sh` | `record` 记内容 sha256 + 块 ID；重启后 `verify` 比对 | 重启后文件丢失，或块 ID 变了（说明元数据没持久化） |
| `check-multiblock.sh` | 可选：上传 140 MB 输入，证明一个文件被切成多个块，每块 2 副本 | 块数 < 2 |
| `run-all.sh` | 依次跑前四项，汇总失败项 | 任一项失败 |

`common.sh` 是共用函数（配置读取、Live 节点解析、块 ID 提取），不单独执行。

## 3. 执行命令

全部在 master 容器内、任意当前目录执行（脚本自己定位所在目录）：

```bash
bash /workspace/tests/hdfs/run-all.sh
```

单跑某一项：

```bash
bash /workspace/tests/hdfs/check-config.sh
bash /workspace/tests/hdfs/check-datanodes.sh
bash /workspace/tests/hdfs/check-readwrite.sh
bash /workspace/tests/hdfs/check-blocks.sh
bash /workspace/tests/hdfs/check-blocks.sh /project/input/hdfs-demo/sample-002.txt
```

重启持久化（两步，中间由 2 号重启集群）：

```bash
bash /workspace/tests/hdfs/check-persistence.sh record
# 2 号：docker compose ... down（不加 --volumes）→ up -d，等两个 DataNode 重新注册
bash /workspace/tests/hdfs/check-persistence.sh verify
```

多块演示（可选，约 280 MB 双副本占用）：

```bash
bash /workspace/tests/hdfs/check-multiblock.sh 140
```

## 4. 预期结果

```text
[hdfs] PASS: fs.defaultFS=hdfs://master:9000
[hdfs] PASS: dfs.namenode.name.dir=/var/lib/hadoop/hdfs/namenode
[hdfs] PASS: dfs.datanode.data.dir=/var/lib/hadoop/hdfs/datanode
[hdfs] PASS: dfs.replication=2
HDFS_CONFIG_PASS
...
[hdfs] PASS: worker1、worker2 的 DataNode 均已注册（共 2 个）
HDFS_DATANODES_PASS
...
[hdfs] PASS: cat 内容与固定输入逐字节一致
HDFS_READWRITE_PASS
...
[hdfs] PASS: 共 1 个块，每个块 2 个副本，覆盖 worker1 与 worker2
HDFS_BLOCKS_PASS
HDFS_TEST_PASS
```

重启验证另有两个独立标记：`HDFS_PERSISTENCE_RECORDED`、`HDFS_PERSISTENCE_PASS`。

成功时退出码 0，任一检查失败退出 1，参数错误退出 2。`check-persistence.sh` 的指纹记录在 `runtime/persistence-001.env`（`runtime/` 已被 `.gitignore` 忽略，不进仓库）。

## 5. 实测记录

| 项 | 结果 | 时间 | 证据 |
| --- | --- | --- | --- |
| `bash -n` 语法检查（8 个脚本） | 通过 | 2026-10-26 | 本地 |
| 正向用例：`run-all.sh`（配置 → 节点 → 读写 → 块） | 全部 PASS，退出 0 | 2026-10-26 | 本地模拟 hdfs |
| 负向用例：配置不符 / 单 DataNode / fsck CORRUPT | 均按预期返回非零 | 2026-10-26 | 本地模拟 hdfs |
| `check-persistence.sh` record → verify | 未改动 PASS、篡改后失败、缺 record 失败、参数错误 exit 2 | 2026-10-26 | 本地模拟 hdfs |
| `check-multiblock.sh 140` | 切成 2 块，每块 2 副本，PASS | 2026-10-26 | 本地模拟 hdfs |
| 三节点真实集群首轮复验（2 号执行） | 文件读写、双副本、容器重建后数据保留均通过；但 `check-blocks.sh` 把「缺失块/欠副本/损坏块」误报为"未包含"并跳过 | 2026-10-29 | 见下方 5.1 |
| 修复后回归（真实 fsck 输出格式：行首空格 + 百分比） | 4/4 PASS：正常通过、CORRUPT 失败、字段全缺失时失败、`run-all` 通过 | 2026-10-29 | 本地模拟 hdfs |
| **三节点真实集群复验（修复版，3 号本机执行）** | **`run-all` 四项全过 → `HDFS_TEST_PASS`；重启后 `HDFS_PERSISTENCE_PASS`；`fsck` 每块两份副本落在两个 worker，缺块/欠副本/损坏均为 0** | 2026-10-31 | 见 [实测记录](../../docs/modules/hdfs/results.md) |

本地验证方式：用 `D:\Git\usr\bin` 下的 coreutils 配一个模拟 `hdfs`（只实现 `getconf` / `dfsadmin -report` / `dfs` / `fsck`），喂真实的 dfsadmin、fsck 输出格式，让脚本原样执行。它证明的是**解析与判定逻辑**正确，不能替代真实集群证据——真实集群必须由 3 号在 master 内重跑并贴原始输出。模拟 harness 放在 `runtime/`（已被忽略），不进仓库。

### 5.1 fsck 摘要行的格式坑（2026-10-29 修复）

2 号在真实集群上复验时发现：`check-blocks.sh` 把三个摘要字段都提示为"未包含"并跳过，但文件本身健康、双副本正常。

根因是我的正则同时锚定了行首和行尾，而真实 `hdfs fsck` 的摘要行是这样的：

```text
 Under-replicated blocks:	0 (0.0 %)
 Missing blocks:		0
 Corrupt blocks:		0
```

三个坑叠在一起：

1. **行首有一个空格** → `^Missing blocks:` 匹配不到；
2. 冒号后是**制表符**而不是空格；
3. 部分计数后面还跟**百分比** `(0.0 %)` → `:[[:space:]]*0$` 也匹配不到。

改法：不再锚定位置，改成「字段名 + 冒号 + 该行第一个整数」：

```bash
sed -n -E "s/^[[:space:]]*${label}[[:space:]]*:[^0-9]*([0-9]+).*/\1/p"
```

这样与缩进、分隔符、后续百分比都无关；同时因为要求字段名后紧跟冒号，`Missing blocks (with replication factor 1):` 这类同前缀字段不会被误配。

另外补了一条保护：**三个字段一条都没识别出来时直接判失败**，不再静默跳过——否则格式再变一次，脚本会在什么都没检查的情况下报通过。`common.sh` 里 `dfsadmin -report` 与块行的解析也一并放宽了行首空白，避免同类问题在别的脚本上复发。

## 6. 说明与边界

- 固定输入在 `fixtures/`：`sample-001.txt`（`hello hadoop`，与模块 README 的演示一致）、`sample-002.txt`（重复演示用）。脚本用 `put -f` 覆盖同名文件，保证反复执行结果一致。
- 脚本只写 `/project/input/hdfs-demo/`，不碰 6、7 号的 `/project/input/wordcount`、`/project/input/mergefile`，也不删别人的目录。
- `check-blocks.sh` 的判据是「每个块的副本 IP 集合 = 两个 Live DataNode 的 IP 集合」，因此它同时等价于「数据块确实分布在两个 Worker 上」，不依赖 fsck 输出里字段名的版本差异。
- 集群起来后需由 3 号建一次基目录，供 6、7 号使用：`hdfs dfs -mkdir -p /project/input /project/output`。
