# 原始输出证据（2026-10-31 实测）

对应 [实测记录](../results.md)。这些文件由取证脚本在 master 容器内逐条命令采集，格式统一为：

```text
$ <实际执行的命令>
<原始输出>
[exit=<退出码>]
```

共 14 个文件、合计约 15 KB。

| 文件 | 采集内容 | 属于哪一轮 |
| --- | --- | --- |
| `00-meta.txt` | 记录时间、容器主机名、`HADOOP_CONF_DIR`、`hdfs version` | 重启前 |
| `01-config.txt` | 5 条 `getconf -confKey` + 两个 XML 全文 | 重启前 |
| `02-datanodes.txt` | `dfsadmin -report` 全文（两个 Live DataNode） | 重启前 |
| `02-safemode.txt` | `dfsadmin -safemode get` | 重启前 |
| `03-readwrite.txt` | `mkdir` / `printf` / `dfs -mkdir` / `put` / `ls` / `cat` / `stat` | 重启前 |
| `04-fsck.txt` | `fsck -files -blocks -locations` 全文（`demo-001.txt`） | 重启前 |
| `05-run-all.txt` | `run-all.sh` 四项检查全文（含 `sample-001.txt` 的 fsck） | 重启前 |
| `06-persistence-record.txt` | `check-persistence.sh record` 的指纹 | 重启前 |
| `07-datanodes-after.txt` | 重启后 `dfsadmin -report` 全文 | 重启后 |
| `07-safemode-after.txt` | 重启后安全模式 | 重启后 |
| `08-persistence-verify.txt` | 重启前后指纹比对 → `HDFS_PERSISTENCE_PASS` | 重启后 |
| `09-cat-after.txt` | 重启后 `cat` 文件内容 | 重启后 |
| `filelist.txt` | 上述文件的字节数清单 | 收尾 |
| `checksums.txt` | 上述文件的 SHA256 | 收尾 |

## 两点说明

1. **容器内时钟为 UTC**，所以时间戳比本地时间早 8 小时（本地 20:53 = 证据里的 12:53）。
2. **重启前后 IP 与 hostname 对调**：重启前 `172.19.0.2` 是 worker2、`172.19.0.3` 是 worker1；重启后反过来。引用时注意区分轮次，详见 [截图索引](../screenshots/README.md)。

## 校验完整性

在本目录执行（Windows 无 `sha256sum` 时用 Git Bash）：

```bash
sha256sum -c checksums.txt
```

`checksums.txt` 覆盖 `00-meta.txt` 到 `09-cat-after.txt` 这 **12 个采集文件**；`filelist.txt` 与 `checksums.txt` 自身不在清单内。
