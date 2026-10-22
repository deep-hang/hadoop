# 5 号：单机模式

使用 `hadoop-base:v0.1`、Java `1.8.0_442`、Hadoop `3.3.6`，显式加载本目录配置，以本地文件系统和本地 MapReduce 执行官方 WordCount。没有常驻 HDFS/YARN 服务。本入口独立于公共 `scripts/dev.*`，也不依赖其他成员的集群。

## 在电脑终端运行

先启动 Docker Desktop 的 Linux 引擎并导入公共镜像。以下命令在项目根目录执行；脚本也支持从其他目录通过完整路径调用。

Windows PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\standalone\manage.ps1 doctor
powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\standalone\manage.ps1 run demo-001
powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\standalone\manage.ps1 verify demo-001
```

Mac/Linux Bash（Windows Git Bash 也可）：

```bash
bash modes/standalone/manage.sh doctor
bash modes/standalone/manage.sh run demo-001
bash modes/standalone/manage.sh verify demo-001
```

不传输入路径时，默认使用 `input/sample.txt` 中的 `hello hadoop`、`hello` 两行。预期输出为 `hadoop=1`、`hello=2`；终端先显示实际词频，再显示 `RESULT_PASS distinct_words=2 total_words=3`，日志应包含 `job_local...`。

## 使用自己的文本

`run <run-id> [输入文件或目录]` 接受宿主机路径，包括项目目录外的文件；相对路径按调用者当前目录解释，含空格/中文的路径加引号。省略路径仍运行默认样例。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\standalone\manage.ps1 run own-001 "D:\data\my-text.txt"
powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\standalone\manage.ps1 run own-002 "D:\data\my texts"
powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\standalone\manage.ps1 verify own-001
```

```bash
bash modes/standalone/manage.sh run own-001 "/path/to/my-text.txt"
bash modes/standalone/manage.sh run own-002 "/path/to/my texts"
bash modes/standalone/manage.sh verify own-001
```

把示例路径替换成实际文件。输入为 UTF-8 纯文本，支持 BOM、CRLF、中文；以空白分词，区分大小写、保留标点（`Hello`、`hello`、`hello,` 分别计数，连续中文不自动切词）。目录读取当前层普通文件，忽略以 `.`、`_` 开头的条目，不递归；子目录、空目录、无效 UTF-8 和压缩文件会失败。空文本文件可以运行，得到 0 个词。

原始输入只读挂载，不修改用户文件。每次运行先保存输入副本到 `runtime/member5/standalone/<run-id>/input/`，再执行作业。`InputCounts.java` 从该副本独立计算预期词频，verify 重新计算并与实际输出比较，不再固定检查两句话，也不信任已有的 expected.tsv 缓存。修改原始输入不会改变旧运行的校验结果。目录内文件名保留；单文件挂载后在副本中名为 `member5-input`。

旧版默认样例 `impl-001` 等没有输入副本的运行，通过旧 config.log 和原固定预期兼容校验。新运行均保存输入副本。

结果保存在宿主机 `runtime/member5/standalone/demo-001/output/`，运行日志保存在同级目录；管理命令日志在 `runtime/member5/standalone/control/`。再次运行必须使用新的 ID，例如 `demo-002`。已有运行目录会明确失败，原结果不会被覆盖或删除；失败的 ID 也不自动重用。

## 入口与配置

| 动作 | 行为 |
| --- | --- |
| `doctor` | 检查 Linux 引擎、Compose 配置和镜像 |
| `run <run-id> [输入路径]` | 使用指定文件/目录或默认样例运行，展示并核对实际词频 |
| `verify <run-id>` | 核对已有结果和 `_SUCCESS` |
| `shell` | 进入带本模式配置的临时容器，`exit` 返回电脑终端 |
| `test` | 在宿主机执行自动测试，需要 Python 3 |

例如进入容器：Windows 执行 `powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\standalone\manage.ps1 shell`；Mac 执行 `bash modes/standalone/manage.sh shell`。

`conf/core-site.xml` 固定 `fs.defaultFS=file:///`，`conf/mapred-site.xml` 固定 `mapreduce.framework.name=local`。`ModeProbe.java` 使用实际的 `JobConf` 检查生效配置；两个 Java 辅助程序均在 `/tmp` 编译，不修改仓库或镜像。`run.sh`、`verify.sh` 是容器内入口；日常使用上述宿主机管理入口。

项目名 `hadoop-m5-standalone`，资源上限 1 CPU/1 GiB，不发布宿主机端口。仓库只读挂载，仅本模块运行目录可写。容器执行完成后自动删除，输出保留；Compose 网络可由下面的限定命令移除：

```text
docker compose --env-file .development -f modes/standalone/compose.yaml -p hadoop-m5-standalone down
```

run-id 只接受字母、数字、`-`、`_`。成功为 0，运行/验证失败为非零，参数错误为 2。没有 Maven、SSH 或额外镜像依赖。Bash/PowerShell 入口共享本目录宿主机辅助逻辑；该辅助逻辑也由成员 5 的伪分布式入口复用。

本模块测试放 [对应 tests/ 子目录](../../tests/standalone/)；实验步骤、结果和交付链接放 [对应 docs/modules/ 子目录](../../docs/modules/standalone-pseudo/)。
