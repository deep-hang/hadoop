# Hadoop 小组项目

公共开发环境已验证；2—7 号继续完成各自模块。统一使用 Java 8、Hadoop 3.3.6 和镜像 hadoop-base:v0.1。

## 怎么开始

1. 按 [Windows / Mac 使用说明](docs/platform-setup.md) 完成第 1—8 步：下载代码、导入镜像、验证环境。
2. 创建自己的 feat/... 分支，按 [目录与分工](docs/project-files.md) 和 [公共接口](docs/interfaces.md) 开发、测试。
3. 推送个人分支，提交 PR（合并申请），由组长审核后合入 main。操作见 [协作规则](docs/contributing.md)。

## 分支怎么用

- **main**：审核通过的正式代码，最终完整项目汇总到这里。
- **feat/...**：每个人日常开发、修改和测试的分支。

流程：**个人分支开发 → 测试 → 提交 PR → 组长审核 → 合入 main**。分支是代码版本的名称，不是文件夹。

## 按需查看

[下载镜像（约 829 MB）](https://github.com/deep-hang/hadoop/releases/download/phase0-image-v0.1/hadoop-base-v0.1.tar.gz) · [三节点启动（2—4 号）](docs/cluster-startup.md) · [模块交接](docs/member-onboarding.md) · [课程要求](docs/requirements.md) · [进度与最终验收](docs/final-acceptance.md) · [验证记录](docs/phase0-status.md)

版本与路径以 [.development](.development) 为准；组长维护镜像看 [构建说明](docker/README.md)。当前开发容器供编译测试使用，三节点集群按启动说明接入。
