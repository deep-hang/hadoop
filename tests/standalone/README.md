# 单机模式的输入、执行与输出测试

负责人：5 号。需要 Python 3.10+、运行中的 Docker Linux 引擎、Compose 和 `hadoop-base:v0.1` 镜像。无需启动 HDFS，也无需安装宿主机 Java。

在电脑终端、项目根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ./modes/standalone/manage.ps1 test
```

Mac/Linux 使用 `bash modes/standalone/manage.sh test`，也可直接运行 `python3 tests/standalone/check-standalone.py`（Windows 用 `python`）。

测试运行真实 Hadoop 本地 MapReduce，检查固定词频、已有输出保护、损坏输出识别、缺少成功标记，以及中文文件名、空格、BOM/CRLF、自定义单文件/多文件/空输入和无效输入。还会检查终端入口从其他目录运行的行为。

成功时退出码为 0；失败返回非零并打印原因。每次创建唯一的 `hadoop-m5-standalone-test-*` 项目；本次输入和结果保存在 `runtime/member5/tests/` 与对应本地运行目录，命令日志及 `result.json` 的位置以 `EVIDENCE` 为准。结束时清理本次 Docker 测试资源并核对原有资源，保留日志便于排查。

测试工具 `support.py` 与伪分布式测试共享。日常网页和演示见 [使用说明](../../docs/modules/standalone-pseudo/README-RUNTIME.md)；这里不包含网页全部交互测试。
