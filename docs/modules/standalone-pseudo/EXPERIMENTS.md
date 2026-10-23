# 成员 5 实验记录与交接

本轮范围：单机、伪分布式代码、配置、自动测试和运行说明。PPT、视频与截图制作暂不纳入。原始任务与后续课程交付要求保留在本目录 README。

## 环境与模式

2026-10-22，Windows 宿主机、Docker Desktop Linux/amd64 引擎，Compose v5.5.1。基础镜像 `hadoop-base:v0.1`，ID `sha256:6d9579105c8651df68fc3fbd5c3addea8706d610a8a005bd85ac734fb8551583`。Java `1.8.0_442`、Hadoop `3.3.6`。初始团队提交 `edab708cb8e24270101505cd77e4b23f6f98806a`。

| 项目 | 单机 | 伪分布式 | 团队完全分布式（对比） |
| --- | --- | --- | --- |
| 文件系统 | file:/// | hdfs://pseudo:9000 | hdfs://master:9000 |
| 常驻 Hadoop 服务 | 0 | NameNode + DataNode | 服务分布在 master/worker1/worker2 |
| 节点 | 1 个执行容器 | 1 个服务容器、1 个 DataNode | 3 个容器、2 个 DataNode |
| 计算方式 | 本地 MapReduce | 本地 MapReduce | 由 2—4 号交付 YARN |
| 资源上限 | 1 CPU / 1 GiB | 2 CPU / 2 GiB | 由对应成员配置 |
| 数据位置 | runtime/member5/standalone | 专用 Docker 卷 | 团队独立数据卷 |

节点/服务/计算方式分别核对：存在 HDFS 不代表作业通过 YARN 分布式调度。本模块日志中的 `job_local...` 与实际 JobConf 一起作为本地计算证据；伪分布式另核对 HDFS 读写。

成员 5 与其他模块可并行开发；成员 6/7 的正式应用依赖 2—4 号集群，不依赖本模块。官方 WordCount 只用于验证两种运行模式，不替代成员 6 的应用实现。

## 复现顺序

完整命令见[单机说明](../../../modes/standalone/README.md)和[伪分布式说明](../../../modes/pseudo/README.md)。电脑启动 Docker，引入已发布镜像，通过公共 verify 后：

1. 单机：doctor → run 新 ID → verify 相同 ID。
2. 伪分布式：doctor → init（停机时）→ up → status → run 新 ID → verify。
3. 在容器中查看 jps、dfsadmin -report、HDFS 输入输出，以及宿主机 Web。
4. restart → verify；down → up → verify，确认数据保留。
5. 两套自动测试顺序运行，测试证据保存在各自随机目录。
6. 结束时对伪分布式执行 down，保留命名卷供之后恢复。单机输出保留在 runtime/member5/。

两个模式的默认输入均为 `hello hadoop\nhello\n`，固定回归预期为 hadoop=1、hello=2。也支持 `run <run-id> [宿主机文本文件或目录]`；省略路径保持默认行为，自定义输入的预期由保存的本次输入独立计算。ID 不能包含路径分隔符，已有 ID 明确失败，旧数据不自动删除。

## 验证记录

最初固定样例版本（自定义输入扩展之前）的实现验证已通过：

| 验证 | 实测结果 | 本机证据（runtime 不提交） |
| --- | --- | --- |
| 单机自动测试 | 11 项检查通过，真实词频正确，失败场景与资源隔离通过 | `runtime/member5/tests/hadoop-m5-standalone-test-3910fb4efe/result.json` |
| 伪分布式自动测试 | 13 项检查通过，初始化保护、HDFS、作业、重启、重建、端口冲突、服务失败及隔离均通过 | `runtime/member5/tests/hadoop-m5-pseudo-test-2e719a67af/result.json` |
| 宿主机管理入口 | Windows PowerShell 的 init 保护、status、restart、stop/up、down/up、verify、logs 均通过；Git Bash doctor/verify 与非法 ID 检查通过 | `runtime/member5/pseudo/control/smoke-*.log` 及两种模式 control 目录 |
| 容器 shell | `/workspace` 正确，仓库只读保护生效 | standalone control 目录 |
| 公共回归 | 7 项契约检查和公共 verify 通过，含 `BASE_API_PASS` | 公共验证输出 |
| 文件保护 | 79 个原文件中，仅授权的 5 份 README 改变；其余 74 个字节一致 | `runtime/member5/scope-audit.json` |

每次自动测试的 `result.json` 包含实际 passed、检查清单、源码 SHA-256、镜像 ID 和基线提交号。Windows/Git Bash 已实测；原生 Mac、Apple 芯片模拟环境尚未实机验证，不能由本机结果替代。

### 干净源码复验

从本地已提交的 `af4274db57448cd1821aaccf344f0ec5d5be4813` 创建全新克隆 `runtime/member5/repro-final/`，确认工作区干净、不含原目录运行数据，再通过克隆中的宿主机入口顺序执行测试：

| 入口 | 实测结果 | 克隆目录内证据 |
| --- | --- | --- |
| Git Bash `modes/standalone/manage.sh test` | passed=true，11 项检查通过 | `runtime/member5/tests/hadoop-m5-standalone-test-a4419a8277/result.json` |
| PowerShell `modes/pseudo/manage.ps1 test` | passed=true，13 项检查通过 | `runtime/member5/tests/hadoop-m5-pseudo-test-24007bcc0c/result.json` |

两套测试均使用随机独立项目，退出后测试容器、网络、卷全部清理；原有其他项目保留。本轮结束时正常伪分布式环境也已 down，演示卷及 `impl-001` 的 HDFS 输入/输出保留，使用正常入口 up 后可 verify。单机 `impl-001` 的输出保留在原源码目录 runtime 中。

伪分布式健康运行期间一次 `docker stats` 采样为 547.4 MiB / 2 GiB；这是单次观测，不代表峰值。两个资源上限与单机上限均由测试检查。新 Bash 脚本语法检查、Python 编译检查、模块文档链接检查均通过。

上述复验对应初版固定样例源码。自定义输入扩展后的测试单独记录，不能用初版测试代替新版验证。复验副本和完整日志在本机忽略目录保留，便于用户核验。

### 自定义输入扩展

新增 InputCounts.java，以独立的流式读取和计数核对实际 Hadoop WordCount 输出。分词规则与 Hadoop 3.3.6 的 [WordCount 源码](https://github.com/apache/hadoop/blob/rel/release-3.3.6/hadoop-mapreduce-project/hadoop-mapreduce-examples/src/main/java/org/apache/hadoop/examples/WordCount.java)一致，支持其 [UTF-8 BOM 处理](https://github.com/apache/hadoop/blob/rel/release-3.3.6/hadoop-mapreduce-project/hadoop-mapreduce-client/hadoop-mapreduce-client-core/src/main/java/org/apache/hadoop/mapreduce/lib/input/LineRecordReader.java)。输入限定为 UTF-8 纯文本；目录不递归。动态校验不代替固定回归测试，测试对自定义数据另列固定答案。

单机保存 runtime 下的输入副本；伪分布式保存 HDFS 输入，借助只读挂载的临时 client 接收宿主机文件，无需重新挂载 HDFS 服务。临时 client 为 1 CPU/1 GiB，服务保持 2 CPU/2 GiB、一个 DataNode；客户端退出自动移除。普通输出保护、数据卷及成员目录边界保持原有规则。

扩展版最终在干净源码副本 `runtime/member5/repro-input-final/` 复验，源码提交 `5ecd76c5c64ddb1f36d09b7f94a6844d77c30249`：

| 验证 | 最终结果 | 副本内证据 |
| --- | --- | --- |
| Git Bash 单机 test | passed=true，18 项通过 | `runtime/member5/tests/hadoop-m5-standalone-test-c22503b461/result.json` |
| PowerShell 伪分布式 test | passed=true，20 项通过 | `runtime/member5/tests/hadoop-m5-pseudo-test-0d8ade4c4b/result.json` |

固定两句样例仍被独立核对。自定义多文件案例的唯一预期为 Apple=2、apple=3、你好=1、世界=2、punct,=2；案例包括中文/空格/`#`/`%` 文件名、BOM/CRLF/Tab/换页符、隐藏文件和空文本。已验证源文件保持原样、修改源文件后旧结果仍可校验、篡改输出失败、已有 ID 拒绝覆盖，以及自定义 HDFS 结果经 restart 和 down/up 后仍正确。

上传将本地文件名转换为编码后的 `file://` URI，避免 Hadoop Put 遇到空格时按默认 HDFS 解释本地路径。测试工具对 stdin 使用原始 UTF-8 字节，避免 Windows 文本管道把 LF 改为 CRLF；对应本机诊断证据为 `runtime/member5/encoded-uri-check.log` 和 `runtime/member5/windows-stdin-check.json`。调试失败记录保留在各自随机报告目录，最终通过结果以以上两行记录为准。

实际宿主机入口也已核验：PowerShell 自定义目录、Git Bash 自定义文件在两种模式均成功，控制日志分别位于 `runtime/member5/standalone/control/custom-host-*.log` 和 `runtime/member5/pseudo/control/custom-final-*.log`。旧版 `impl-001` 仍可校验，伪分布式正常环境结束后已 down 并保留数据卷。原生 Mac 仍未实机验证。

本机另提供可修改的 `runtime/member5/custom-input-example.txt`：三行输入的结果为 Docker=2、Hadoop=3、Python=1，已通过真实单机作业验证。它属于本机忽略文件，不是运行依赖；其他人可传自己的 UTF-8 文本路径。所有自动测试资源已清理，原有其他项目保留。最终运行源码与上述报告的 SHA-256 一致，仅本地提交，等待用户核验后才考虑推送。

文件范围审计可在电脑终端复验：

```text
python tests/standalone/check-scope.py edab708
```

该命令从 Git 读取原始版本，与当前文件逐一比较 SHA-256，检查新增文件归属，只允许五份原有 README 修改；成功返回 0，违规返回非零。它不会回退或覆盖文件。

## 排错与保留数据

- Docker 未启动：启动 Linux 引擎后执行 doctor。
- 镜像缺失：按公共平台说明导入；模块不会构建、拉取或覆盖基础镜像。
- 未初始化：在服务停止、数据目录符合保护条件时显式 init，不使用强制格式化。
- 端口占用：检查错误，必要时设置本模式的 `M5_PSEUDO_WEB_PORT` 后重试；不停止占用程序。
- up 等待失败：查看控制日志、服务 logs、healthcheck 输出；不删卷碰运气。
- 输出已存在：使用新的 run-id；失败运行的目录也保留供排查。
- 初始化遇到非空目录/锁：先确认本项目服务和现有数据，不删除其他项目的资源。

控制日志文件名使用 UTC 时间；宿主机本地时间为 Asia/Shanghai。`runtime/` 不提交 Git。测试只清理带本次随机项目标签的容器、网络和卷；其他项目仅做只读前后对照。

## 提交与审核

只提交成员 5 的两种模式、两套测试及本目录材料。原有文件仅五个 README 属于授权修改；其余原文件按基线逐一 SHA-256 核对。

**当前状态：仅本地开发和提交，尚未推送分支、尚未创建 PR。按用户要求，须由用户先核验并明确同意，再推送 `SgRpg/hadoop:feat/standalone-pseudo`，之后向 `deep-hang/hadoop:main` 提 PR，由组长复验、审核和合并。**

用户可先按两个模式 README 自行运行，或从 Git 查看本地功能分支相对 `edab708` 的文件差异；也可查看上述自动测试 JSON 和文件范围审计报告。

参考：[Hadoop 3.3.6 单节点文档](https://hadoop.apache.org/docs/r3.3.6/hadoop-project-dist/hadoop-common/SingleCluster.html)。保留独立卷的行为见 [Docker 卷说明](https://docs.docker.com/engine/storage/volumes/)。
