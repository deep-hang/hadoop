# 伪分布式服务、持久化与运行结果测试

负责人：5 号。测试在全新专属卷中运行真实 NameNode/DataNode、HDFS 操作、本地 MapReduce、重启和容器重建。

## 在电脑终端执行

前置：Python 3、Docker Linux 引擎、Compose、已导入公共镜像；为伪分布式容器预留 2 GiB 以内的运行空间。先完成公共环境验证。

Windows，项目根目录：

```powershell
python tests/pseudo/check-pseudo.py
```

Mac/Linux：

```bash
python3 tests/pseudo/check-pseudo.py
```

也可调用本模式 `manage.ps1 test` / `manage.sh test`。每项通过显示 `PASS`，最终成功退出 0；任何断言、命令、清理或隔离检查失败退出非零。通常需数分钟，不将容器 Up 作为通过依据。

## 覆盖场景

1. 未初始化启动失败，NameNode/DataNode 非空目录分别拒绝格式化并保留哨兵。
2. 显式初始化、重复初始化保护；运行期间跨容器再次 init 被卷锁拒绝。
3. 两个 HDFS 服务、恰好 1 个 Live DataNode、安全模式关闭、HDFS 可访问。
4. 仅回环地址发布 Web；通过 NameNode JMX 独立核对节点数。
5. 固定输入 mkdir/put/ls/cat 与正确作业结果，实际 JobConf 和 `job_local` 证明采用本地 MapReduce。
6. 已有路径重复运行失败，原结果保持不变。
7. restart 后与 down/up 重建后，输入、输出及 NameNode VERSION 保持一致。
8. 占用端口时启动失败，原占用程序保持运行。
9. 当前平台可用的宿主机入口支持其他工作目录及非法 ID 检查。
10. 只在测试容器终止 DataNode，容器清理另一服务并以非零退出，排除 OOM。
11. 限定资源清理与其他项目资源前后对照。

还通过 tools profile 的临时 client 和真实只读宿主机挂载测试自定义单文件/多文件目录、中文/空格路径、BOM/CRLF、空文本、输入快照和结果篡改；期望值在 Python 测试中独立列出，不使用运行时参考计算作为测试答案。自定义结果也经历 restart 和 down/up 持久化验证。临时客户端会自动移除，常驻 DataNode 数仍为 1。

测试复用成员 5 的 `tests/standalone/support.py`，因此运行时保留完整仓库。两种模式测试顺序执行。

## 隔离与日志

每次使用 `hadoop-m5-pseudo-test-<随机串>`、独立网络/卷和随机宿主机 Web 端口；不会初始化或删除 `hadoop-m5-pseudo` 的普通演示卷。端口冲突用例只占用本机随机端口。

测试退出前收集日志、检查资源标签，再对本次随机测试项目执行清理，确认资源消失且原有容器/网络/卷保留；不用全局 prune。不能证明归属时拒绝删除并报告失败。

详细命令、退出码、源码 SHA-256、镜像 ID、基线提交号和 `result.json` 位于 `runtime/member5/tests/<项目名>/`。成功和失败均输出 `EVIDENCE`。如宿主机同时有人主动启停其他环境，前后对照可能报告外部状态变化，应查看日志核实，不自动恢复或删除其他资源。
