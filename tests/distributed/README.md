# 三节点启动、网络连通与持久卷测试

负责人：2 号。先按 [三节点编排使用说明](../../compose/README.md) 初始化并启动正式集群，再在电脑终端的项目根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ./tests/distributed/check-skeleton.ps1 -Project hadoop-distributed-recovery
```

脚本检查三个节点的名称、相互解析、运行用户和数据卷写权限。成功输出 `SKELETON_CHECK_PASS` 并返回 0，失败返回非零。实际集群使用其他项目名时，相应修改 `-Project`；该参数默认值与编排说明一致。

这项检查使用 PowerShell。Mac 的启动、服务就绪及 HDFS/YARN 检查命令见上方编排说明。名称和网络检查通过后，还需运行其中的 HDFS、YARN 测试；容器重建后数据保留的验证结果见 [联合验证记录](../../docs/modules/distributed/integration-results.md)。
