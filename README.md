# Hadoop 小组项目

组长 Phase 0 公共底座。统一开发镜像、工作目录、公共接口及校验入口已完成，**容器构建和基础运行验证通过**。已发布至 GitHub 的 `common/phase0-bootstrap` 独立分支；正式发布 `v0.1-bootstrap` 稳定标签前由组长审阅。

## 统一环境

| 项目 | 固定值 |
| --- | --- |
| Linux | Ubuntu 22.04 Jammy（基础镜像使用 SHA256 digest 锁定） |
| JDK | Eclipse Temurin 8u442-b06，`java` 版本 `1.8.0_442` |
| Hadoop | Apache Hadoop 3.3.6（下载包使用官方 SHA512 校验） |
| 项目镜像 | `hadoop-base:v0.1`，本地已构建并验证 |
| 容器平台 | `linux/amd64` |
| Java / Hadoop | `/opt/java/openjdk` / `/opt/hadoop` |
| 工作目录 | `/workspace`（挂载仓库根目录） |

版本选择遵循 [Apache Hadoop Java 兼容说明](https://cwiki.apache.org/confluence/spaces/HADOOP/pages/100827883/Hadoop+Java+Versions)。宿主机需要 Git、可用的 Linux 容器引擎与 Compose v2 或更高版本：Windows/Mac 使用 Docker Desktop，Linux 可使用 Docker Engine + Compose 插件；不要求本机安装 JDK 或 Hadoop。镜像构建需要能访问 Docker Hub 和 Apache Archive，首次下载体积较大；慢速下载时可使用 [官方安装包缓存](docker/README.md)。

## 先选择自己的系统

直接打开 [不同系统使用说明](docs/platform-setup.md)，选择 Windows、Intel Mac、M 系列 Mac 或 Linux。无需提前向组长登记系统，按对应步骤完成镜像获取和基础验证即可。

## 第一次使用：按顺序完成

1. 打开 [不同系统使用说明](docs/platform-setup.md)，选自己的系统，依次完成第 1—8 步，每步都有操作位置、命令和成功结果。
2. 镜像导入或构建后验证，看到 BASE_API_PASS 和 PASS: frozen Java/Hadoop versions, paths, compiler and Hadoop API loading。
3. 进入容器确认工作目录和版本，再退出。
4. 在电脑终端 [创建自己的任务分支](docs/platform-setup.md#task-branch)，按 [联调验收](docs/member-onboarding.md) 开发与交付。

以后按 [每天操作顺序](docs/platform-setup.md#daily) 使用，不必重复安装或构建。Windows 的 Bypass 参数仅作用于此次脚本进程，不修改永久执行策略。

基础验证通过代表开发环境可用；dev 为一次性开发容器，不启动 Hadoop 守护进程、不格式化文件系统、不映射集群端口。集群与应用由对应成员实现。

## 目录与负责人

| 目录 / 文件 | 内容 | 负责人 |
| --- | --- | --- |
| `docker/` | 冻结基础镜像、公共入口 | 1 号 |
| `compose/bootstrap.yaml` | 基础镜像构建与开发入口 | 1 号 |
| `compose/` 后续集群文件 | master / worker1 / worker2 网络、卷、启动编排 | 2 号 |
| `config/common/`、`.development`、`scripts/` | 公共环境与接口 | 1 号 |
| `config/hdfs/` | HDFS 配置 | 3 号 |
| `config/yarn/` | YARN、MapReduce 配置 | 4 号 |
| `modes/standalone/`、`modes/pseudo/` | 单机与伪分布式模式 | 5 号 |
| `apps/wordcount/` | WordCount 完整闭环 | 6 号 |
| `apps/mergefile/` | MergeFile 完整闭环 | 7 号 |
| `tests/`、`docs/` | 各模块验证与说明 | 对应模块负责人 |

## 协作与交付

以 [.development](.development) 和 [公共接口](docs/interfaces.md) 为开发契约；公共文件修改须由组长协调。各模块从功能分支开发，完成本地容器测试后提交 PR，组长审核后合并；禁止直接推送 main。详见 [协作规则](docs/contributing.md)。

当前机器环境、已做验证、待办及老师要求中的差异记录在 [Phase 0 验证报告](docs/phase0-status.md)。各系统安装、镜像导入、构建和报错处理见 [不同系统使用说明](docs/platform-setup.md)。
