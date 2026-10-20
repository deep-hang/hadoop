# 成员接入与联调验收

先让每个人跑通同一底座，再逐层接入模块。当前完成的是公共环境；三节点集群、运行模式和两个应用尚未实现。底座通过不等于全部模块已经能拼起来。

## 第一步：按自己的系统验收底座

直接按 [不同系统使用说明](platform-setup.md) 选择 Windows、Intel Mac、Apple 芯片 Mac 或 Linux 的步骤。不需要提前向组长报告系统或处理器；每人在自己的电脑验证通过后即可开始本模块开发，公共 Java/Hadoop 版本按仓库约定使用。

当前镜像固定 `linux/amd64`。Windows 需 Docker Desktop 的 Linux 容器及可用虚拟化组件；Intel/AMD 电脑与该架构匹配。Apple M 系列等 ARM 电脑需要模拟运行，速度可能较慢，必须实机验证。Docker Desktop 提供模拟支持，但这不能替代组员机器上的验收，见 [Docker 架构与模拟说明](https://docs.docker.com/build/building/multi-platform/)。目前实测环境为组长的 Windows 11 / Intel 电脑。

安装 Git 和适合本机的 Docker 后，启动 Docker，执行：

```text
git clone --branch common/phase0-bootstrap https://github.com/deep-hang/hadoop.git
cd hadoop
```

获取基础镜像，二选一：

- 推荐首轮接入时由组长分享已验证的 `hadoop-base-v0.1.tar.gz`，成员在下载目录执行 `docker load --input hadoop-base-v0.1.tar.gz`。这会导入 `hadoop-base:v0.1`，不需要重新下载 Hadoop。不要把压缩包上传 Git。Docker 支持直接导入 gzip 压缩的镜像包，见 [官方 load 说明](https://docs.docker.com/reference/cli/docker/image/load/)。
- 不方便传文件时，在项目根目录按 README 执行 build，自行构建固定版本的镜像；首次下载可能较慢。

再回到项目根目录验证。Windows PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 doctor
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 verify
```

macOS/Linux 的 Bash：

```bash
bash scripts/dev.sh doctor
bash scripts/dev.sh verify
```

最后应输出：

```text
BASE_API_PASS
PASS: frozen Java/Hadoop versions, paths, compiler and Hadoop API loading
```

每位成员都要在自己电脑上取得这个结果。失败时发完整错误及系统/处理器信息给组长，先解决接入问题，不另装一套本机 Hadoop 来绕过。镜像包只提供环境，项目源码仍从 GitHub 获取。

## 第二步：从同一底座开分支

按自己的任务选择一条命令，只执行对应的那一条：

| 任务 | 分支命令 |
| --- | --- |
| 2 号 | `git switch -c feat/distributed` |
| 3 号 | `git switch -c feat/hdfs` |
| 4 号 | `git switch -c feat/yarn-mapreduce` |
| 5 号 | `git switch -c feat/standalone-pseudo` |
| 6 号 | `git switch -c feat/wordcount` |
| 7 号 | `git switch -c feat/mergefile` |

这一步基于刚克隆的同一公共分支进行；不要从独立空仓库开始，也不要互相复制整个项目目录。每人只改负责的模块，保持 `.development`、`docker/`、公共脚本及 `config/common/` 不变。公共问题先反馈组长，由组长协调修改。

当前尚无 main 或正式集成分支。成员可以先提交、推送自己的功能分支；组长指定集成目标后再申请对应 PR，不自行把功能合入公共底座分支。

## 第三步：先交付可连接的最小模块

| 阶段 | 交付人 | 组长和下游实际验收什么 |
| --- | --- | --- |
| 节点骨架 | 2 号 | master、worker1、worker2 同时运行；容器名与 hostname 一致；节点间可解析并连接 |
| HDFS | 2 + 3 号 | 在同一编排中两个 DataNode 注册；能上传、读取文件；持久数据不因普通重启而被格式化 |
| YARN | 2 + 4 号 | 同一编排中两个 NodeManager 注册；实际作业可以提交、完成；提供结果和节点信息 |
| 单机/伪分布式 | 5 号 | 各模式独立启动、运行、验证，卷与端口不和完全分布式环境混用 |
| 应用 | 6 / 7 号 | build、run、verify 接口与公共契约一致；在上游交付的真实集群中运行并核对结果 |

2、3、4 号应尽早一起跑一次最小链路，完成后就交给 6、7 号联调，不等 PPT 和视频全部做完。6、7 号此前可以在公共容器中开发代码、输入数据和本模块测试。

### 容易拼不起来的关键点：应用在哪个容器里运行

`compose/bootstrap.yaml` 的 `dev` 只是开发环境，当前没有 master，也没有接入未来集群的网络和配置。不能在这个容器里填一个 `hdfs://master:9000`，就认为它自动连接了集群。

2 号交付集群骨架时，须同时向 3、4、6、7 号说明：

1. 使用哪个 Compose 文件，完整启动、停止、查看日志的命令是什么。
2. 从哪个容器提交应用（建议初期统一从 master），如何执行应用脚本。
3. 该容器是否挂载仓库到 `/workspace`，并加载 3、4 号交付的 HDFS/YARN 配置。
4. 三节点属于哪个容器网络，master 与 Worker 的名称是否可解析。

上述连接由 2、3、4 号共同实现。6、7 号复用这一提交环境，不能各自另起互不相通的集群。

## 每个模块交接时必须附带

- 源码所在分支、提交号和修改目录。
- 前置条件：需要哪些上游已通过的能力。
- 在干净源码上可复制执行的构建、启动、运行、验证、停止命令，以及执行位置（宿主机/容器）。
- 固定输入数据、预期输出与实际验证结果；失败返回非零退出码。
- 新增端口、卷和配置，以及是否涉及公共接口；不能把手工改容器当成已交付。

组长在集成副本中按这些命令复现，复现通过才接收；发生冲突先联系文件负责人。最终还要用一份新克隆的源码完成从启动到两种应用结果验证的整套演示，之后才能称为完整项目验收通过。
