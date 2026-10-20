# 成员接入与联调

## 第一步：通过本机验证

按 [Windows / Mac 使用说明](platform-setup.md) 完成镜像导入、verify 和任务分支创建，再开始模块开发。

## 第二步：按顺序交付

| 顺序 | 负责人 | 验收内容 |
| --- | --- | --- |
| 三节点骨架 | 2 号 | master、worker1、worker2 同时运行且可互相解析、连接 |
| HDFS | 2 + 3 号 | 两个 DataNode 注册，文件可上传、读取，普通重启不重新格式化 |
| YARN | 2 + 4 号 | 两个 NodeManager 注册，真实作业可提交并完成 |
| 单机 / 伪分布式 | 5 号 | 各模式可启动、运行和验证，数据卷与端口互不冲突 |
| 应用 | 6 / 7 号 | build、run、verify 符合公共接口，接入真实集群核对结果 |

2、3、4 号尽早交付最小可运行集群；6、7 号此前可先在开发容器编写代码和测试数据。相互依赖的配置和编排先按下方联合验证，不要求某人独自等其他人全部合入 main。

## 第三步：约定应用运行位置

当前 dev 容器没有接入正式三节点集群。2、3、4 号共同交付以下内容，6、7 号复用同一环境：

1. 集群 Compose 文件及启动、停止、查看日志命令。
2. 应用从哪个容器提交（统一从 master），执行什么命令。
3. 提交容器挂载仓库到 /workspace，并加载 HDFS/YARN 配置。
4. 三节点使用同一网络，master、worker1、worker2 可解析连接。

## 第四步：提交交接材料

测试放 [tests/ 对应子目录](../tests/README.md)，实验材料放 [docs/modules/ 对应子目录](modules/README.md)。

1. 分支、提交号、修改目录、所需上游能力。
2. 可复制的构建、启动、运行、验证、停止命令，写明在电脑还是容器内执行。
3. 固定输入、预期输出、实际结果；失败时返回非零退出码。
4. 新增端口、卷、配置和公共接口变化。

组长在干净源码中复现通过后接收。最终用新克隆源码完成集群启动与两个应用演示，才算整体验收通过。

## 联调前避免这几种误判

| 容易卡住的地方 | 负责人和验收方式 |
| --- | --- |
| Docker 显示容器已启动，Hadoop 还没就绪 | 2—4 号提供就绪检查与失败日志；HDFS 两个 DataNode、YARN 两个 NodeManager 实际注册后再提交应用 |
| 进程启动后容器立刻退出，或教程要求 SSH | 复用 [已提供的公共启动方式](cluster-startup.md)，不能只在容器里手动改一次 |
| 命名卷无法写入或重启丢数据 | 2、3 号保证 UID 1000 的权限，持久化 NameNode/DataNode；只对全新目录格式化，普通停止与重启不删卷 |
| 有两个 Worker，但只在本地运行作业 | 4、6、7 号核对生效的 HDFS/YARN 配置，提供真实 application/job ID 和成功结果 |
| 数据太少，只看到一个 Worker 处理任务 | 3 号证明数据块分布；4、6、7 号用合适的输入分片与调度设置，记录实际任务所在节点。节点注册截图不能代替两节点参与证据 |
| 内存不足、任务长期排队、M 系列特别慢 | 2、4 号交付实测的 Docker CPU/内存分配、YARN/任务资源参数及启动等待方式，不凭基础 verify 推断三节点一定可跑 |
| MergeFile 各人理解不同 | 7 号先按课程材料固定合并规则、是否去重/排序、输出格式，再提交固定输入与预期输出供组长确认 |
| 单机、伪分布式和完全分布式相互影响 | 5 号使用独立配置、数据卷、Compose 项目及端口；演示时明确启动和停止哪种模式 |

先打通“2 号骨架 → 3 号 HDFS → 4 号 YARN 简单作业”，再接两个应用；5 号可并行开发，6、7 号可先编译和验证局部逻辑。各模块按上游合并通知同步，方法见 [协作规则](contributing.md)。

最终演示前，组长用干净源码按全部步骤复现，记录源码提交号、镜像 ID、配置、输入与预期输出；在演示电脑提前完成下载，不临场依赖首次下载或安装。

运行与分片依据：[Hadoop 官方集群配置](https://hadoop.apache.org/docs/r3.3.6/hadoop-project-dist/hadoop-common/ClusterSetup.html)、[MapReduce 输入与任务说明](https://hadoop.apache.org/docs/r3.3.6/hadoop-mapreduce-client/hadoop-mapreduce-client-core/MapReduceTutorial.html)。

<a id="joint-check"></a>
## 相互依赖的 PR，怎样在合入前联合验证

2 号编排依赖 3、4 号配置，而配置测试又需要编排，不能三个人互相等。采用“各自推送草稿 PR → 组长合到临时目录测试 → 分别审核原 PR”的流程。

1. 2—4 号分别推送自己的分支、创建 Draft PR，写明缺少的配套 PR。骨架可先单独验收；只有临时保持容器运行时，明确标为骨架。
2. 待三个配套分支都有可运行候选内容，组长从干净 main 建独立联调工作目录。在电脑终端的项目根目录执行以下命令（仅首次创建，三个远端分支必须已存在）：

~~~text
git fetch origin
git worktree add -b integration/cluster ../hadoop-cluster-integration origin/main
git -C ../hadoop-cluster-integration merge --no-edit origin/feat/distributed
git -C ../hadoop-cluster-integration merge --no-edit origin/feat/hdfs
git -C ../hadoop-cluster-integration merge --no-edit origin/feat/yarn-mapreduce
~~~

3. 切到新目录，按 2 号正式运行说明及 3、4 号测试验证。先停止旧正式集群，避免同名 Compose 项目和端口同时运行；使用保留数据的 down，不删卷。记录各分支提交号、启动命令、结果和问题。
4. 有冲突或失败时由对应成员在原功能分支修复。组长 fetch 并把更新的分支合入联调目录后复验；新提交出现后，旧测试结果不能直接当成新版本已通过。
5. 联合测试通过后，将原 2—4 号 PR 标为 Ready，由组长审核并逐个使用 Create a merge commit 合入 main。中间过渡提交注明配套 PR，全部配套合入后才通知下游“集群可用”。
6. 再从最新 main 核对启动与真实作业，通知 6、7 号同步 main。不把联调分支作为成员的新开发入口，也不以直接推送 main 代替原 PR 审核。

共同验证是运行证据；单独 XML 语法或容器 Up 只能证明局部步骤。各模块提交阶段性成果时必须写明哪些已实测、哪些仍依赖配套模块。最终录制及交付按 [组长验收清单](final-acceptance.md)。
