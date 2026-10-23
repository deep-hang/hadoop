# Hadoop：成员 5 单机与伪分布式模式

本模块提供单机、伪分布式两套可运行环境，并通过本地网页展示真实 Hadoop WordCount 作业、存储过程和验证结果。适用于成员 5 交付、组长复验和其他组员在自己电脑上复现。

本文为独立新增的交付 README，现有根 README 和各模块 README 保留原样。

## 两种模式有什么区别

| 项目 | 单机模式 | 伪分布式模式 |
| --- | --- | --- |
| 文件系统 | 本地文件系统，`file:///` | 单节点 HDFS，`hdfs://pseudo:9000` |
| 计算方式 | 本地 MapReduce | 本地 MapReduce |
| 常驻 Hadoop 服务 | 无 | NameNode、DataNode |
| 作业输入输出 | 本模块本地运行目录 | 本模块 HDFS 输入输出目录 |
| HDFS 副本数 | 不适用 | 1 |
| YARN | 不启动 | 不启动 |

单机流程：网页输入 → 保存快照 → 本地文件 → 本地 MapReduce → 本地输出 → 验证。

伪分布式流程：网页输入 → 保存快照 → 上传 HDFS → 本地 MapReduce → 写回 HDFS → 验证。NameNode 管理文件与数据块位置，DataNode 保存实际数据块。

## 1. 准备环境

| 依赖 | 要求 |
| --- | --- |
| Git | 用于拉取分支 |
| Python | 3.10 或更高版本，可通过 `python` 或 `python3` 调用 |
| Docker | Linux 容器引擎已启动，Docker Compose 可用 |
| 统一镜像 | `hadoop-base:v0.1` |
| 镜像内版本 | Java `1.8.0_442`、Hadoop `3.3.6` |

网页运行使用 Python 标准库及原生 HTML/CSS/JavaScript，不需要安装 npm 或第三方 Python 包。宿主机无需另装 Java、Hadoop。

Docker 安装、统一镜像下载导入和公共环境验证见 [Windows / Mac 环境说明](../../platform-setup.md)。镜像不会随 Git 分支下载。

Windows 可先检查：

```powershell
python --version
docker compose version
docker info --format '{{.OSType}}'
docker image inspect hadoop-base:v0.1 --format '{{.Id}}'
```

第三条预期为 `linux`。镜像不存在时，按公共环境说明下载镜像包，然后使用实际文件路径导入：

```powershell
docker load --input "C:\实际下载目录\hadoop-base-v0.1.tar.gz"
```

## 2. 获取功能分支

新建源码副本时执行：

```powershell
git clone --branch feat/standalone-pseudo https://github.com/SgRpg/hadoop.git hadoop-member5
cd hadoop-member5
```

后续相对路径命令均在项目根目录执行。请保留完整仓库，伪分布式和网页入口会复用成员 5 单机目录的辅助实现。

已有正在开发的仓库时，可使用上述命令另建副本，避免切换分支干扰未提交工作。

## 3. 启动 Hadoop 网页

先打开 Docker Desktop，等待 Linux 引擎就绪。

Windows PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\standalone\web-plus.ps1
```

Windows 也可在文件资源管理器中双击 `modes/standalone/web-plus.cmd`。

Git Bash、Mac/Linux Bash：

```bash
bash modes/standalone/web-plus.sh
```

启动后自动打开浏览器，也可以访问 [Hadoop 网页](http://127.0.0.1:19875/)。网页名称为 **Hadoop**。

从其他当前目录启动时，使用你电脑上的入口完整路径。例如：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\你的项目目录\hadoop-member5\modes\standalone\web-plus.ps1"
```

终端窗口需保持运行；关闭浏览器不会停止服务或作业。停止网页服务时，在启动它的终端按 `Ctrl+C`。

可选参数：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\standalone\web-plus.ps1 --port 19876 --no-open --max-input-bytes 1048576
```

默认端口为 `19875`，默认输入上限为 1 MiB。新旧网页共用仓库级独占锁，同一仓库不能同时启动两个网页服务；换端口不能绕过独占锁。

## 4. 首次核验

### 单机模式

1. 首页检查 Docker 和统一镜像状态。
2. 在输入框中输入：

```text
hello hadoop
hello 你好 世界
```

3. 选择“单机模式”，开始运行。
4. 查看真实阶段、文件系统 `file:///`、计算框架 `local`、本地作业 ID 及实际输入输出路径。
5. 预期总词数为 5，不同词数为 4：

```text
hello    2
hadoop   1
你好     1
世界     1
```

结果列表显示顺序可能按词频排序，验证依据是完整词频及成功标记。

### 伪分布式模式

1. 真正首次使用空环境时，进入“环境管理”，明确确认“初始化”，再启动 HDFS。
2. 已有初始化元数据时，只需启动，不需要重复初始化。服务停止本身不表示尚未初始化。
3. 确认就绪检查通过：NameNode、DataNode 存活，恰好 1 个 Live DataNode，安全模式关闭，HDFS 根目录可访问。
4. 回首页输入文本或上传 TXT，选择“伪分布式模式”运行。
5. 在详情页查看 HDFS 上传、整个本地 MapReduce 作业、HDFS 输出与验证，以及实际逻辑路径、存储卷和采集时间。
6. 点击“查看实际输入／输出”浏览 HDFS 文件；通过页面按钮打开实际发布的 NameNode Web 地址，默认端口为 `19870`。

普通运行不会自动初始化或格式化。受保护的初始化会拒绝未初始化但数据目录非空等危险状态，页面保留具体错误。

### 双模式对照

HDFS 就绪后，使用同一文本点击“双模式对照”。系统保存共同输入，顺序运行两种模式，再分别验证并比较全部词频。

只有共同输入一致、两侧独立验证通过、完整输出一致时，才显示“对照通过”。详情页展示两侧独立流程、存储差异、实际配置和阶段耗时；缺少结果或证据时不会补造通过结论。

## 5. 文本与文件规则

- 支持直接输入文本，或通过“＋”按钮上传一个 `.txt` 文件，两者互斥。
- 文件必须为 UTF-8，支持 BOM、中文及 CRLF。默认上限 1 MiB。
- 空 TXT 和已输入的纯空白文本可以运行，结果为 0 个词；未提供任何输入时不提交。
- 按官方 WordCount 的 Java 分词规则处理空格、制表和换行等分隔符，区分大小写、保留标点。连续中文不会自动进行中文分词。
- 每次运行使用新 ID，已有输入或输出不覆盖。快照保存后，修改原输入不会改变旧运行的验证依据。
- 首页未提交内容保存在页面内存中；刷新首页会清除。已提交任务可以刷新、返回或重新打开原链接查看。

## 6. 结果、历史与文件查看

- 结果页分别显示作业、验证和报告状态，支持完整词频搜索、排序、每页 50 项。
- 详情展示实际文件系统、计算框架、本地作业 ID、输入 SHA-256、镜像与源码版本。
- 可以下载完整 TSV、日志、离线报告 ZIP，或单独重新生成报告。
- 历史记录支持查看和重新验证。重新验证读取真实本地/HDFS 数据，历史成功不能代替当前验证。
- 验证失败时，可查看缺词、多词、错误计数、重复结果、格式错误和成功标记诊断，并下载差异 TSV。
- 从失败记录恢复输入会创建新 ID，保留旧输出和原失败证据。
- 文件浏览范围限定在成员 5 运行目录，预览最多 64 KiB、200 行；只读，不提供任意命令或删除功能。
- 关闭 Docker 后仍可查看已保存结果与报告；重新运行、读取 HDFS 或重新验证需要相应环境恢复。

## 7. 数据与团队资源隔离

| 数据 | 位置 |
| --- | --- |
| 单机输入输出 | `runtime/member5/standalone/<id>/` |
| 增强入口记录 | `runtime/member5/console/` |
| 网页任务与上传 | `runtime/member5/web/` |
| HDFS 输入 | `/project/input/member5/<id>/` |
| HDFS 输出 | `/project/output/member5/<id>/` |
| HDFS 持久数据 | 成员 5 伪分布式项目专用命名卷 |

单机项目名为 `hadoop-m5-standalone`，伪分布式为 `hadoop-m5-pseudo`，不使用团队三节点集群的网络或数据卷。伪分布式服务上限 2 CPU/2 GiB，临时客户端上限 1 CPU/1 GiB；实际同机资源仍与其他程序共享。

“停止”保留服务数据，“移除容器”保留数据卷。取消作业只清理当前临时客户端，不使用整个项目的 `down` 取消作业。

运行产物被 Git 忽略。其他人拉取分支后获得相同功能，但不会获得你的历史、输入输出、报告、截图或 Docker 卷，需自行运行生成。

## 8. 常见问题

| 提示或现象 | 处理方式 |
| --- | --- |
| 此仓库的网页服务已启动 | 直接打开现有页面；重启前在原终端按 Ctrl+C，不能通过换端口启动第二个服务 |
| 网页端口被其他程序占用 | 在没有本仓库网页服务运行时用 `--port` 换端口，不停止其他程序 |
| Docker 无法连接 | 打开 Docker Desktop，等待 Linux 引擎就绪，再刷新环境状态 |
| 缺少统一镜像 | 按公共环境说明导入 `hadoop-base:v0.1` |
| HDFS 未就绪 | 查看状态和日志；确认已有初始化数据时启动，真正首次使用才显式初始化 |
| 任务忙碌 | 打开当前任务链接，等待结束或明确取消；不隐式排队 |
| 结果验证失败 | 查看失败阶段、日志和差异；不覆盖旧目录，通过恢复输入创建新运行 |
| 刷新首页后未提交文本消失 | 当前未实现浏览器草稿持久化；提交后的输入和结果可从历史恢复 |

## 9. 自动测试与更多文档

在项目根目录运行新增增强网页单元测试及真实 Docker 集成测试：

```powershell
python -B tests/standalone/test_web_plus.py
python -B tests/pseudo/check-web-plus.py
```

集成测试需要 Docker 和统一镜像，使用随机项目、专用卷与端口，核对归属后清理测试资源。涉及 Docker 资源清单对照的回归应顺序运行。

本机已通过：增强网页单元 24 项及集成 16 项、原单机 18 项、伪分布式 20 项、原增强终端、原网页和公共环境回归。详细版本和统计口径以验收记录为准。

- [增强网页完整说明](WEB-PLUS.md)
- [增强网页验收记录与未验证范围](WEB-PLUS-ACCEPTANCE.md)
- [终端中文菜单说明](CONSOLE.md)
- [原单机管理入口](../../../modes/standalone/README.md)
- [原伪分布式管理入口](../../../modes/pseudo/README.md)
- [公共环境准备](../../platform-setup.md)
- [分支交付说明](PUSH-NOTES.md)

Windows PowerShell、CMD、Git Bash 与本机内置 Chromium 已实测。原生 Mac/Linux、全部浏览器及大规模多用户性能未实测。本工具定位为本机实验与验收入口。
