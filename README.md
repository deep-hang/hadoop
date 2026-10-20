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

## 快速开始（Windows PowerShell）

组员首次接入先看 [成员上手与联调验收](docs/member-onboarding.md)：获取同一源码、导入共享镜像或自行构建、在自己的电脑通过验证，再开始模块开发。

在仓库根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 doctor
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 build
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 verify
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 shell
```

`Bypass` 仅作用于此次脚本进程，不修改系统执行策略。Linux/macOS 对应使用 `bash scripts/dev.sh doctor|build|verify|shell`（每次选择一个动作）。

不使用脚本也可以：

```powershell
docker compose --env-file .development -f compose/bootstrap.yaml config --quiet
docker compose --env-file .development -f compose/bootstrap.yaml build
docker compose --env-file .development -f compose/bootstrap.yaml run --rm -T dev bash tests/verify-base.sh
docker compose --env-file .development -f compose/bootstrap.yaml run --rm dev bash
```

校验预期最后输出 `PASS: frozen Java/Hadoop versions, paths, compiler and Hadoop API loading`。它验证基础环境，不代表集群或应用已完成。`dev` 是一次性开发容器，不启动任何 Hadoop 守护进程，不格式化文件系统，不映射集群端口。

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
