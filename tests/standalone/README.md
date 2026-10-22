# 单机模式的输入、执行与输出测试

负责人：5 号。测试使用真实 Hadoop 本地作业，不是模拟输出。固定输入/预期由 `modes/standalone/` 提供；不读取成员 6 的应用输入。

## 在电脑终端执行

前置：Python 3、Docker Linux 引擎、Compose、已导入 `hadoop-base:v0.1`。不需要在宿主机安装 Java/Hadoop。

Windows，在项目根目录：

```powershell
python tests/standalone/check-standalone.py
```

Mac/Linux：

```bash
python3 tests/standalone/check-standalone.py
```

也可以用本模式 `manage.ps1 test` 或 `manage.sh test`；从其他目录通过脚本完整路径调用也有效。每项通过显示 `PASS`，完整通过退出 0；任一断言、命令、清理或隔离检查失败退出非零。

## 覆盖内容与证据

- Compose 仓库只读、1 CPU/1 GiB 限制。
- 实际 JobConf 的本地文件系统、本地计算配置，真实 `job_local`、无 HDFS/YARN 服务。
- `hadoop=1`、`hello=2`，输出已存在时失败并保持原内容，输入缺失不创建运行目录。
- 结果错误、缺词、多词、重复结果以及缺少 `_SUCCESS` 时失败。
- 当前平台可用的 PowerShell/Bash 宿主机入口从其他目录调用，非法 run-id 返回 2。
- 本次资源清理，以及其他容器、网络和数据卷的前后对照。

每次创建 `hadoop-m5-standalone-test-<随机串>` 项目。`support.py` 是成员 5 测试辅助模块，也供伪分布式测试复用；不修改公共测试。两套测试顺序运行，避免把另一套测试的资源变化当成外部资源变化。

命令日志、源码 SHA-256、镜像 ID、基线提交号及最终 `result.json` 在 `runtime/member5/tests/<项目名>/`，最后输出 `EVIDENCE` 路径。单机测试输出保存在 `runtime/member5/standalone/<项目名>/` 供检查，均不提交 Git。测试修改的错误结果仅限本次创建的输出，随后恢复。

清理前检查资源标签，只清理随机测试项目，不操作普通演示项目和其他成员资源。失败也记录日志；无法证明资源归属时停止删除并报告失败。缺少引擎或镜像等前置条件时直接报错。
