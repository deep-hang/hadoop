# Hadoop：成员 5 精简运行交付

本分支从团队 main（edab708）建立，交付单机、伪分布式、网页和终端运行功能。运行源码与已验证开发版本 58381cc 一致；不包含成员 5 的自动测试程序、运行记录、输入输出产物或 Docker 镜像。

## 获取与环境准备

```powershell
git clone --branch codex/member5-runtime https://github.com/SgRpg/hadoop.git hadoop-member5
cd hadoop-member5
```

需要 Python 3.10+、已启动的 Docker Linux 引擎、Docker Compose，以及统一镜像 `hadoop-base:v0.1`（Java 1.8.0_442、Hadoop 3.3.6）。网页和终端只使用 Python 标准库，无需 npm 或第三方 Python 包；宿主机无需安装 Hadoop 或 Java。

统一镜像不会随 Git 下载，安装与镜像导入方法见[公共环境准备](../../platform-setup.md)。保留完整基础仓库，尤其是根目录 `.development`。

```powershell
python --version
docker compose version
docker info --format '{{.OSType}}'
docker image inspect hadoop-base:v0.1 --format '{{.Id}}'
```

## 启动网页

在仓库根目录运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\standalone\web-plus.ps1
```

也可双击 `modes/standalone/web-plus.cmd`。Mac/Linux 或 Git Bash 使用 `bash modes/standalone/web-plus.sh`。从其他目录启动时，为启动器指定自己的实际完整路径，不要求使用开发者相同的目录。

页面默认地址为 [Hadoop](http://127.0.0.1:19875/)。终端需要保持运行，按 Ctrl+C 停止服务。可传入 `--port 19876`、`--no-open`、`--max-input-bytes 1048576`。同一仓库只允许一个新旧网页服务实例，换端口不能绕过独占锁。

## 两种模式的操作

1. 打开 Docker Desktop，等待 Linux 引擎就绪；进入首页检查环境。
2. 输入文本，或用“＋”上传 UTF-8 TXT（支持 BOM）；选择单机模式并开始运行。
3. 观察真实执行过程、高频词和完整词频，以及本地输入输出路径。
4. 要运行伪分布式，先到环境管理显式初始化空环境，再启动 HDFS。已有初始化数据时只启动，不重复初始化。
5. 等待 NameNode、DataNode 存活、1 个 Live DataNode、安全模式关闭且根目录可访问，再运行伪分布式。
6. 查看 HDFS 上传、计算和输出步骤；点击实际输入输出浏览文件，或打开 NameNode 页面。

| 项目 | 单机 | 伪分布式 |
| --- | --- | --- |
| 存储 | 本地文件系统 `file:///` | 单节点 HDFS `hdfs://pseudo:9000` |
| 计算 | 本地 MapReduce | 本地 MapReduce |
| 常驻服务 | 无 | NameNode、DataNode |
| 输入输出 | 本模块本地目录 | 本模块 HDFS 目录 |

两种模式都不启动 YARN。伪分布式副本数为 1，不是团队三节点集群。网页中分别运行两种模式，不提供新建双模式对照。结果页已移除重新验证、重新生成报告、TSV 和离线 ZIP 下载；后台自动验证、快照与报告仍保留。高频词与完整词频位于执行过程下方。

示例输入 `hello hadoop` 换行 `hello`，预期 `hello=2`、`hadoop=1`。词按 Java WordCount 的空白分隔，区分大小写、保留标点；连续中文不会自动分词。默认输入上限 1 MiB。空 TXT 或已输入的纯空白文本可以得到 0 个词；没有提供输入时不提交。

## 终端入口

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\standalone\console.ps1
```

中文菜单提供环境检查、单机/伪分布式运行、历史、真实验证、HDFS 查看及服务管理。`console.py --help` 查看命令；原 `manage.ps1` / `manage.sh` 和原网页 `web.py` 也保留。

本精简分支不交付成员 5 自动测试文件，`manage test` 等测试命令不可作为本分支的验收入口。日常运行和每次作业自动进行的结果验证不依赖这些测试文件。测试程序继续保存在原开发分支。

## 资源、路径与常见问题

- 运行数据进入 `runtime/member5/`，不随分支上传；HDFS 数据进入本项目专用命名卷。
- Compose 项目为 `hadoop-m5-standalone`、`hadoop-m5-pseudo`。仓库只读挂载，停止或移除伪分布式容器保留数据卷；取消只清理当前作业客户端。
- 默认 NameNode 页面端口为 19870，网页读取实际映射。端口被占用时明确失败，不停止其他程序。
- 不要求统一仓库路径，也不需要修改 Windows 注册表。Windows 宿主机文件读写支持长路径，作业输入通过本次专属系统临时目录挂载，并核对清理归属。
- Docker 对配置文件的绑定挂载仍受宿主机路径、共享与引擎限制。检查提示 `CONFIG_MOUNT_FAILED` 时，先处理目录共享或改用较短、Docker 可读取的目录；程序不会自动格式化或搬迁配置。
- Docker 不可连接时启动引擎；镜像缺失时按公共文档导入；HDFS 未就绪时检查状态和日志。停止不意味着未初始化，运行不会隐式格式化。
- 提示网页已启动时使用现有页面；需要重启时在原终端停止。浏览器首页刷新会清空未提交输入，已提交任务可从历史恢复。
- Windows PowerShell、CMD、Git Bash、内置 Chromium 及真实 Docker 作业在开发版本已验证；原生 Mac/Linux 与全部浏览器未实测。此分支另做源码一致性、依赖导入、配置解析和启动帮助检查，不把这些检查冒充新的完整 Hadoop 回归。

本分支只包含运行交付；组长核验后按团队流程决定是否合并，不自动合并团队 main。
