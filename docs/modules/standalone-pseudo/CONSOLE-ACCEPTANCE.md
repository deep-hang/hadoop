# 统一入口优化：验收记录

## 实现与基线

本轮从 `feat/standalone-pseudo` 的 `1a7142a` 开始，在成员 5 目录新增统一操作入口、结构化 Hadoop 检查、记录存储、HTML 报告及测试；团队公共文件和其他成员文件保持原样。原有文件只更新获准的五份 README。

实现包括中文菜单、自动 ID、运行摘要、共同输入双模式对照、历史及真实复验、HDFS 快捷查看、离线 HTML 报告。不新增持久化演示入口、PPT 或视频；原有持久化和进程故障测试继续保留。

代码验收版本：`eef19f3`；其后的文档提交不改变运行代码。干净源码副本位于本机 `runtime/member5/repro-console-verified/`，通过本地 Git clone 创建，不复制旧 runtime 或未跟踪源码。

## 实测环境

- Windows，Asia/Shanghai；Python 3.13.16。
- Docker Desktop Linux/WSL2，Compose v5.5.1。
- `hadoop-base:v0.1`，Java `1.8.0_442`，Hadoop `3.3.6`。
- 镜像 ID：`sha256:6d9579105c8651df68fc3fbd5c3addea8706d610a8a005bd85ac734fb8551583`。
- 宿主机 `LongPathsEnabled=0`，不修改该系统设置。

## 结果登记

| 检查 | 结果 |
| --- | --- |
| 增强入口单元测试 | 23 项通过，包括可选 Node.js 报告脚本检查 |
| 公共契约检查 | 7 项通过 |
| 公共基础环境 | `BASE_API_PASS` |
| 双模式增强入口集成 | 15 项检查通过；另一个隔离单机项目的资源清理检查通过 |
| 原单机回归 | 18 项通过 |
| 原伪分布式回归 | 20 项通过，包含重启/重建、端口冲突与 DataNode 退出处理 |
| 文件范围及校验 | 通过：开工 108 个文件中 103 个 SHA-256 不变，变化仅获准五份 README |

增强集成使用随机独立项目和卷，顺序验证默认输入、自定义多文件、BOM/CRLF/中文及特殊文件名、空文件、完整结果比较、自动 ID、旧入口导入、HDFS 预览、结果篡改、真实临时容器中断、包装器和离线报告。测试结束核对资源标签和其他项目状态，再仅清理本次测试资源。

干净副本中的详细证据：

- 单元测试：`runtime-unit.log`。
- 增强集成：`runtime-enhanced.log`；JSON 位于 `runtime/member5/tests/hadoop-m5-pseudo-test-2ba63184b0/result.json`，配套单机隔离项目为 `hadoop-m5-standalone-test-fbf1918dd5`。
- 单机回归：`runtime-standalone.log`；JSON 位于 `runtime/member5/tests/hadoop-m5-standalone-test-e26afc3969/result.json`。
- 伪分布式回归：`runtime-pseudo.log`；JSON 位于 `runtime/member5/tests/hadoop-m5-pseudo-test-f890822e33/result.json`。

四份集成/回归 JSON 的源码提交和镜像 ID 均一致，记录的源码 SHA-256 与当前交付代码逐项相符。总核对结果保存在本机 `runtime/member5/console-development/final-validation.json`；开工基线核对为同目录 `final-baseline-audit.json`。按最初团队版本 `edab708` 审计，74 个不属于授权 README 的原始文件保持不变。

本轮新增 13 个实现、测试和文档文件，只更新原有五份成员 5 README；既有基础实现文件未修改。测试退出码均为 0，专属容器、网络和卷已清理，其他项目的前后资源/运行状态检查通过。原有正常演示数据卷继续保留。

供本机用户直接查看的报告副本位于 `runtime/member5/console-review-eef19f3/`，其中 `compare/index.html`、`standalone/index.html`、`pseudo/index.html` 分别是相同自定义输入的对照、单机和伪分布式报告。该输入总计 7 个词、5 个不同词，包括中文和作为普通文本显示的 `<script>x</script>`。入口不修改原输入；测试之后显式修改了原文件以验证快照独立性。报告副本及其 TSV/JSON 均保留供手动核验，不提交 Git。

## 已定位并修复的问题

1. Git Bash 在 `MSYS_NO_PATHCONV=1` 下向原生 Python 传递 `/d/...`：包装器显式转换入口与输入路径。
2. Windows 文件共享读取造成短暂原子替换失败：有限重试，始终保留原子替换语义，不截断目标记录。
3. 深层测试路径加长临时 JSON 文件名达到 Windows 260 字符限制：缩短临时文件名和报告版本目录，并加入深路径测试。

失败阶段日志保留在忽略的 `runtime/member5/console-development/` 和此前 `repro-console-final/` 副本；这些失败记录不能作为最终通过证据。最终结果以本页登记的验证副本及其 JSON 为准。

## 验证边界与交接

PowerShell、CMD、Git Bash 在当前 Windows 机器验证。原生 Mac/Linux 未实测。

报告搜索与分页脚本通过最小 DOM 模型执行检查；HTML 数据完整性、用户文本转义和离线资源自包含通过自动测试。内置浏览器安全策略拒绝打开本地 `file://` 页面，因此真实浏览器视觉效果及原生文件打开体验留待用户手动核验，不声称已完成视觉验收，也不通过其他方式绕过该限制。

用户从 [统一入口说明](CONSOLE.md) 启动菜单，依次完成环境检查、单机运行、显式 HDFS 初始化/启动、双模式对照、历史复验及报告查看。报告保存的是采集时间的证据；测试卷清理后，其中 HDFS 路径不再对应在线数据。

当前只保留本地功能分支提交；未经用户核验并明确同意，不推送、不创建 PR、不合并团队 main。
