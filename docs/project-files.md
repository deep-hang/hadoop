# 项目文件说明

想知道“每个文件是什么、里面放什么”看本文；安装与启动按 [Windows / Mac 使用说明](platform-setup.md)。

## 1. 先看懂项目根目录

“项目根目录”就是下载得到的 hadoop 文件夹。以点开头的文件不是报错或多余文件，而是工具使用的配置。

| 目录 / 文件 | 里面是什么、有什么用 | 谁负责 |
| --- | --- | --- |
| [README.md](../README.md) | 项目首页：开工入口、统一版本与分支用途 | 所有人阅读 |
| [.github/CODEOWNERS](../.github/CODEOWNERS) | 指定所有文件由组长审核，配合 GitHub 分支保护生效 | 1 号 |
| [.changes/](../.changes/) | 公共变更记录：改了什么、影响谁、怎么验证和回退 | 公共文件修改者 |
| [apps/](../apps/) | 两个应用的代码和测试输入 | 6、7 号 |
| [compose/](../compose/) | 开发容器，以及完全分布式三节点集群的网络、挂载和启动 | bootstrap 开发容器由 1 号维护；完全分布式编排由 2 号开发 |
| [config/](../config/) | Hadoop 的公共配置、HDFS 与 YARN 配置 | 1、3、4 号分工 |
| [docker/](../docker/) | 统一 Java/Hadoop 环境的构建配方和启动入口 | 1 号 |
| [docs/](../docs/) | 使用说明、接口、协作和验收文档 | 根目录公共说明由 1 号维护；成员材料放 [modules/](modules/README.md) |
| [modes/](../modes/) | 单机、伪分布式两种运行方式 | 5 号 |
| [scripts/](../scripts/) | 检查环境、验证和进入容器的快捷脚本 | 1 号 |
| [tests/](../tests/) | 验证公共底座与后续模块是否正常 | common/ 由 1 号维护；其余按模块分目录，见 [测试分工](../tests/README.md) |
| [.development](../.development) | 全组公共参数：版本、目录、节点名、端口和应用路径 | 1 号协调维护 |
| [.dockerignore](../.dockerignore) | 构建镜像时不传入的内容，如 Git 记录、日志、编译产物 | 1 号 |
| [.gitattributes](../.gitattributes) | 统一文本换行为 LF，避免 Windows/Mac 脚本换行问题 | 1 号 |
| [.gitignore](../.gitignore) | Git 不跟踪的内容，如编译产物、日志、编辑器配置和本地缓存 | 1 号 |

## 2. apps/ 与 modes/：组员实现功能的位置

| 位置 | 内容与用途 |
| --- | --- |
| [apps/wordcount/](../apps/wordcount/) | 6 号实现单词统计；src/ 放源码，input/ 放测试输入 |
| [apps/mergefile/](../apps/mergefile/) | 7 号实现文件合并；src/ 放源码，input/ 放多文件测试输入 |
| [modes/standalone/](../modes/standalone/) | 5 号实现单机运行，补充运行入口、测试和说明 |
| [modes/pseudo/](../modes/pseudo/) | 5 号实现单节点 HDFS 及伪分布式配置、数据持久化和验证 |

这些目录当前只有交接说明或占位文件，具体功能尚未实现。应用后续需提供 build.sh（编译）、run.sh（运行）、verify.sh（核对结果），参数见 [公共接口](interfaces.md)。

.gitkeep 是让 Git 保留空目录的占位文件，不是程序，不需要运行。各目录的 README.md 是该模块的任务说明，成员实现后应更新实际使用方法。

## 3. config/ 与 compose/：配置和连接环境

| 文件 / 目录 | 内容与用途 |
| --- | --- |
| [config/common/hadoop-env.sh](../config/common/hadoop-env.sh) | 设置 Java、Hadoop 和日志目录 |
| [config/common/core-site.xml](../config/common/core-site.xml) | 公共 Hadoop 配置；当前保持空配置，不连接 HDFS |
| [config/common/workers](../config/common/workers) | 预留 worker1、worker2 节点名，不会自动创建或启动节点 |
| [config/hdfs/](../config/hdfs/) | 3 号补充 HDFS 地址、数据目录、副本等配置，当前只有说明 |
| [config/yarn/](../config/yarn/) | 4 号补充 YARN / MapReduce 服务配置，当前只有说明 |
| [compose/bootstrap.yaml](../compose/bootstrap.yaml) | 定义 dev 开发容器：使用统一镜像，把电脑项目目录挂到 /workspace；不启动集群 |

**完全分布式放在哪里？** 它由以下部分共同组成，不单独放在 modes/：

| 位置 | 完全分布式中的作用 | 负责人 |
| --- | --- | --- |
| compose/ 后续集群文件（建议 distributed.yaml） | 创建 master、worker1、worker2 三个容器，连接网络、数据卷与启动命令 | 2 号 |
| config/hdfs/ | 配置 NameNode、两个 DataNode 与文件存储 | 3 号 |
| config/yarn/ | 配置 ResourceManager、两个 NodeManager 与 MapReduce 计算 | 4 号 |

三部分接入同一编排后，才是可运行的完全分布式集群。当前集群文件及服务配置尚未实现；bootstrap.yaml 只有开发容器。modes/ 只放 5 号负责的单机、伪分布式，6、7 号应用后续接入完全分布式集群验证。

.development 中的 HDFS 地址、服务名和端口是后续模块共同遵守的约定，写在文件里不代表服务已经运行。config/common/ 在构建镜像时复制进去，修改电脑上的配置不会自动改动已有镜像。

## 4. docker/、scripts/、tests/：环境与检查工具

| 文件 / 目录 | 内容与用途 |
| --- | --- |
| [docker/Dockerfile](../docker/Dockerfile) | 镜像配方：安装固定 Java/Hadoop、校验下载包、创建开发用户；组员直接下载镜像即可 |
| [docker/entrypoint.sh](../docker/entrypoint.sh) | 容器启动时检查工具和配置，再执行指定命令；不自动启动集群 |
| [docker/cache/](../docker/cache/) | 组长构建时可用的 Hadoop 官方安装包缓存，不是供组员导入的 Docker 镜像包 |
| [scripts/hadoop-node.sh](../scripts/hadoop-node.sh) | 公共无 SSH 启动脚本，处理显式初始化、master/worker 服务和退出清理；由集群编排调用 |
| [scripts/dev.ps1](../scripts/dev.ps1) | Windows 快捷入口 |
| [scripts/dev.sh](../scripts/dev.sh) | Mac 快捷入口 |
| [scripts/windows-enable-wsl.ps1](../scripts/windows-enable-wsl.ps1) | 可选的 Windows 组件准备工具，需要管理员权限；日常开发不运行，不会自动重启 |
| [tests/common/check-cluster.py](../tests/common/check-cluster.py) | 使用独立配置复验三节点、真实 YARN 作业和重启数据保留 |
| [tests/common/check-contract.py](../tests/common/check-contract.py) | 检查公共版本、路径、目录、XML、换行和文档链接 |
| [tests/common/verify-base.sh](../tests/common/verify-base.sh) | 容器内检查 Java/Hadoop，并实际编译运行 Hadoop API 探针 |
| [tests/common/verify-entrypoint.sh](../tests/common/verify-entrypoint.sh) | 检查容器启动入口的报错、参数和退出码行为 |

dev.ps1 与 dev.sh 的动作对应如下：

| 动作 | 用途 |
| --- | --- |
| doctor | 检查 Docker 和项目配置 |
| verify | 调用基础运行验证，首次接入必须通过 |
| shell | 进入开发容器，在 /workspace 编译、运行和测试 |
| config / build | 维护者检查编排 / 重建镜像；组员按使用说明导入即可 |

普通组员不必直接执行 tests/ 下的每个文件，先用 verify 完成基础验收；自己的模块另补功能测试。

测试已按 common/、distributed/、hdfs/、yarn-mapreduce/、standalone/、pseudo/、wordcount/、mergefile/、integration/ 分开。负责人和提交规则见 [测试目录](../tests/README.md)。

## 5. docs/：需要时查哪份说明

| 文档 | 什么时候看 |
| --- | --- |
| [platform-setup.md](platform-setup.md) | 首次安装、下载导入、进入容器和每天使用 |
| [project-files.md](project-files.md) | 了解项目目录与文件，也就是本文 |
| [cluster-startup.md](cluster-startup.md) | 2—4 号接入公共启动脚本、复验三节点能力 |
| [interfaces.md](interfaces.md) | 写模块前：核对节点名、路径与应用脚本接口 |
| [contributing.md](contributing.md) | 开发提交前：核对分支、修改范围、测试与 PR 规则 |
| [member-onboarding.md](member-onboarding.md) | 模块交接时：按顺序联调集群、配置和应用 |
| [windows-setup.md](windows-setup.md) | Windows 安装 Docker 时缺少 WSL/虚拟化组件 |
| [final-acceptance.md](final-acceptance.md) | 组长安排进度、安装讲解、整体验收、PPT/视频汇总 |
| [phase0-status.md](phase0-status.md) | 查看已完成的验证、镜像标识和当前未完成内容 |
| [requirements.md](requirements.md) | 核对课程验收要求，以及需向老师确认的事项 |

实验步骤、结果和截图按成员放在 [docs/modules/](modules/README.md)；docs/ 根目录保留公共说明，不让大家共同编辑一份实验报告。

## 6. 自己该改哪些文件

1. 先按任务号找到自己的模块目录，读其中 README.md 和公共接口，再开发。
2. 只提交源码、配置、必要测试输入和说明；编译产物、日志、镜像包不放进 Git。
3. 公共镜像、公共脚本、.development 等需要变更时，先由组长协调，避免影响其他成员。
