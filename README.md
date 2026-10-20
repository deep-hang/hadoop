# Hadoop 小组项目

Phase 0 公共底座已完成并通过本地运行验证；2—7 号模块由各成员继续实现。代码分支：common/phase0-bootstrap。

## 从这里开始

1. 按 [Windows / Mac 使用说明](docs/platform-setup.md)第 1—8 步下载代码、导入镜像并验证。
2. 创建自己的任务分支，按 [公共接口](docs/interfaces.md) 开发。
3. 完成模块测试，按 [联调说明](docs/member-onboarding.md) 交接。

[下载镜像包（约 829 MB）](https://github.com/deep-hang/hadoop/releases/download/phase0-image-v0.1/hadoop-base-v0.1.tar.gz) · [镜像发布页](https://github.com/deep-hang/hadoop/releases/tag/phase0-image-v0.1)

2、3、4 号开发前阅读 [公共集群启动说明](docs/cluster-startup.md)，复用已验证的启动方式。

[项目文件说明](docs/project-files.md)：每个目录和文件是什么、里面有什么、谁负责修改。

## 统一环境

| 项目 | 固定值 |
| --- | --- |
| 系统 / 平台 | Ubuntu 22.04 / linux/amd64 |
| JDK | Temurin 8u442-b06（1.8.0_442） |
| Hadoop | 3.3.6 |
| 镜像 | hadoop-base:v0.1 |
| Java / Hadoop 目录 | /opt/java/openjdk / /opt/hadoop |
| 工作目录 | /workspace，挂载电脑上的项目根目录 |

版本、路径和节点约定以 [.development](.development) 为准。当前 dev 容器只供开发，不启动 HDFS/YARN 集群。

## 目录与负责人

| 目录 / 文件 | 内容 | 负责人 |
| --- | --- | --- |
| docker/、config/common/、scripts/、.development | 基础镜像、公共配置与工具 | 1 号 |
| compose/bootstrap.yaml | 开发容器 | 1 号 |
| compose/ 后续集群文件 | 完全分布式三节点网络、卷和启动 | 2 号 |
| config/hdfs/ | HDFS 配置 | 3 号 |
| config/yarn/ | YARN / MapReduce 配置 | 4 号 |
| modes/standalone/、modes/pseudo/ | 单机、伪分布式 | 5 号 |
| apps/wordcount/ | WordCount | 6 号 |
| apps/mergefile/ | MergeFile | 7 号 |
| tests/common/、docs/ 根目录 | 公共测试和说明 | 1 号 |
| tests/ 各模块子目录 | 本模块测试，见 [测试分工](tests/README.md) | 对应负责人 |
| docs/modules/ | 分模块实验材料，见 [文档分工](docs/modules/README.md) | 对应负责人 |

[协作规则](docs/contributing.md) · [验证记录](docs/phase0-status.md) · [课程验收要求](docs/requirements.md)

组长维护镜像时使用 [构建说明](docker/README.md)，组员直接下载导入即可。
