# 截图索引（2026-10-31 实测）

对应 [实测记录](../results.md)，共 7 张，按证据链顺序编号。原始文件名为 UUID 形式，这里已重命名为可读名称，内容未改动。

| 文件                                       | 画面内容                                                                                                            | 对应验收项              |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| `01-overview-live-nodes.png`               | 9870 Summary：Live Nodes 2、Dead Nodes 0、**Under-Replicated Blocks 0**、Blocks Pending Deletion 0                  | 两节点在线、无欠副本    |
| `02-datanodes-in-operation.png`            | 9870 Datanodes 页：worker1、worker2 均 In operation，各自 Num of Blocks                                             | 两个 DataNode 注册      |
| `03-runall-config-datanodes-readwrite.png` | 终端：`run-all` 前半——配置四项 PASS、Live DataNode 两个、读写五项 PASS（13 字节、副本 2、cat/get 一致）             | 配置生效 + 注册 + 读写  |
| `04-browse-directory-replication-2.png`    | 9870 Browse `/project/input/hdfs-demo`：4 个文件，**Replication 列全是 2**，Block Size 128 MB                       | 副本数 2、块大小默认值  |
| `05-fsck-healthy-full.png`                 | 终端：`fsck -files -blocks -locations` 全文——Status HEALTHY、`Live_repl=2`、Missing/Under-replicated/Corrupt 全 0   | 文件健康、无缺块        |
| `06-fsck-counters-test-pass.png`           | 终端：fsck 计数 + 块 1 副本位置 + `HDFS_BLOCKS_PASS` + **`HDFS_TEST_PASS`**                                         | 每块 2 副本、自动化通过 |
| `07-restart-persistence.png`               | 终端：重启后 report 尾段、`Safe mode is OFF`、verify 前后指纹一致、`HDFS_PERSISTENCE_PASS`、`cat` 输出 hello hadoop | 重启不重新格式化        |

