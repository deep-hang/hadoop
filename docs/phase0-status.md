# Phase 0 验证记录

日期：2026-10-20（Asia/Shanghai）。公共底座已通过本地验收，基于已验证的公共底座建立 main，作为默认集成分支；v0.1-bootstrap 稳定标签尚未创建。

## 实测环境

Windows 11 / Intel；Git 2.53.0；Docker Desktop 4.96.0、CLI 29.9.1、Compose 5.6.0。WSL2 与虚拟机平台已配置，重启后 Linux 容器可运行。

## 已通过的验证

| 项目 | 结果 |
| --- | --- |
| 版本和下载校验 | 固定 JDK digest，Hadoop 官方 SHA512 一致 |
| 静态检查 | 7 项公共契约检查及 Bash / PowerShell 语法检查通过 |
| 入口行为 | 缺少工具/配置、退出码、带空格参数，在 Git Bash 和 Linux 容器验证通过 |
| 构建与运行 | doctor、build、verify 通过；Java/javac 1.8.0_442、Hadoop 3.3.6、Hadoop API 探针通过 |
| 干净源码 | 新克隆到含中文和空格的目录，使用已有镜像通过 doctor / verify |
| 镜像分发 | 导出、重新导入后镜像 ID 一致；上传大小及 SHA256 一致，无需登录的下载请求成功 |

Mac 尚未实机验收。公共三节点启动能力已按下文复验；正式集群、HDFS/YARN 模块、运行模式和两个应用由对应成员交付。

## 测试目录调整复验

公共测试已移至 tests/common/，新增各模块测试与实验材料目录。7 项契约检查、全仓库本地文档链接、Bash 语法和入口行为测试通过；PowerShell doctor / verify、Git Bash 的 Bash verify 均通过，继续使用原镜像。Mac 宿主机仍未实测。

## 已分发镜像

[GitHub 发布页](https://github.com/deep-hang/hadoop/releases/tag/phase0-image-v0.1) · [下载镜像包](https://github.com/deep-hang/hadoop/releases/download/phase0-image-v0.1/hadoop-base-v0.1.tar.gz)

- 镜像：hadoop-base:v0.1，linux/amd64，用户 hadoop（UID 1000）。
- 镜像 ID：sha256:6d9579105c8651df68fc3fbd5c3addea8706d610a8a005bd85ac734fb8551583。
- 压缩包大小：828,594,929 字节。
- 压缩包 SHA256：0a1f1e6b5148c2d74811fab39b4667c4ead199930052ac28dd99a40eb3700453。

## 后续工作

1. 成员按 [使用说明](platform-setup.md) 完成本机验收并开发。
2. 组长按 [联调要求](member-onboarding.md) 集成，确认 [课程验收差异](requirements.md)。
3. 公共环境有改动时重新构建验证，再更新镜像分发和记录。

版本依据：[Apache Java 兼容说明](https://cwiki.apache.org/confluence/spaces/HADOOP/pages/100827883/Hadoop+Java+Versions)、[Hadoop 3.3.6 官方 SHA512](https://archive.apache.org/dist/hadoop/common/hadoop-3.3.6/hadoop-3.3.6.tar.gz.sha512)。

## 开工前流程核对（2026-10-20）

已回读 GitHub：目前仅 deep-hang 有仓库写权限，没有待接受邀请；需由组长收齐用户名并邀请成员。公共分支要求组长审核已生效，镜像附件公开可下载；当前未配置自动构建/集群测试。

镜像实际检查：javac、jar 可用，mvn、ssh、sshd 未包含。补齐提交推送、同步上游、服务启动、配置归属、提交容器和联调证据约定；未实现成员正式模块；公共集群启动能力另按下文复验。

老师已接受 Docker 部署；组员本机验收、正式三节点配置及应用演示仍须分别完成。

## 公共三节点启动复验（2026-10-20）

使用现有 hadoop-base:v0.1 镜像、公共启动脚本和独立测试配置，在 Windows / WSL2 上实测：

- master、worker1、worker2 启动成功，两个 DataNode 和两个 NodeManager 注册成功。
- Hadoop 自带 WordCount 示例通过真实 YARN 执行，8 个输入文件得到 hadoop=8000、hello=8000；两个 worker 均产生任务容器日志。
- 未初始化时拒绝启动，非空且无 VERSION 的目录拒绝格式化，重复初始化保留已有元数据。
- 三个节点重启后重新就绪，HDFS 作业结果仍一致；主动终止 DataNode 后，该节点以失败状态退出。
- 日志与 result.json 保存在 runtime/ 随机测试项目目录；测试退出清理自己的容器、网络和卷。

复验命令及正式模块接入见 [公共集群启动说明](cluster-startup.md)。无需重新下载镜像，此结果不替代成员正式模块验收。

## 正式集成入口调整（2026-10-20）

从已验证的底座建立 main，设为 GitHub 默认分支；要求 PR、1 次批准及 @deep-hang 代码所有者审核，新增提交使旧批准失效，禁止普通成员强推和删除。保留所有者维护权限，无待迁移的开放 PR。

README、Windows/Mac 克隆步骤、提交与同步流程已统一到 main。旧底座分支在确认已完整合入 main 后删除；不改变镜像与集群运行配置，提交历史保留。
