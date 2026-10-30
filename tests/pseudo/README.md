# 伪分布式服务、持久化与运行结果测试

负责人：5 号。需要 Python 3.10+、运行中的 Docker Linux 引擎、Compose 和 `hadoop-base:v0.1` 镜像。测试会创建、初始化并启动自己的单节点 HDFS，无需手动执行 `init`。

在电脑终端、项目根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ./modes/pseudo/manage.ps1 test
```

Mac/Linux 使用 `bash modes/pseudo/manage.sh test`，也可直接运行 `python3 tests/pseudo/check-pseudo.py`（Windows 用 `python`）。与单机测试依次执行，便于核对资源保留情况。

覆盖显式初始化和重复初始化保护、1 个 Live DataNode、Web 节点信息、HDFS 上传/读取、真实本地 MapReduce 结果、自定义输入和输出保护，以及服务重启/容器重建后的数据与元数据保留。测试末尾会在自己的测试容器中终止 DataNode，检查容器能否正确停止，而不会操作已有演示容器。

每次使用独立的 `hadoop-m5-pseudo-test-*` 项目和新卷，网页端口由 Docker 自动分配；结束时只删除本次测试容器和卷，并核对原有资源。成功返回 0，失败返回非零；原始日志和 `result.json` 保存在输出的 `EVIDENCE` 路径。

复用 [单机测试工具](../standalone/support.py)。日常启动与演示见 [使用说明](../../docs/modules/standalone-pseudo/README-RUNTIME.md)。本测试使用单节点 HDFS 和本地 MapReduce，不依赖或验证 2—4 号的三节点集群。
