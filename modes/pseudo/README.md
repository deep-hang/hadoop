# 5 号：伪分布式模式

使用原基础镜像，在一个容器内运行独立 NameNode、DataNode 进程，提供单节点 HDFS。计算方式为**本地 MapReduce 读取/写入 HDFS**；不启动 YARN。无需等待成员 2—4 的三节点集群。

## 首次启动与运行（电脑终端）

前置条件：Docker Linux 引擎可用、已导入 `hadoop-base:v0.1`。以下命令在项目根目录执行。

Windows PowerShell，逐条执行，失败先查看日志：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\pseudo\manage.ps1 doctor
powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\pseudo\manage.ps1 init
powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\pseudo\manage.ps1 up
powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\pseudo\manage.ps1 status
powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\pseudo\manage.ps1 run demo-001
powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\pseudo\manage.ps1 verify demo-001
```

Mac/Linux Bash（Windows Git Bash 也可）：

```bash
bash modes/pseudo/manage.sh doctor
bash modes/pseudo/manage.sh init
bash modes/pseudo/manage.sh up
bash modes/pseudo/manage.sh status
bash modes/pseudo/manage.sh run demo-001
bash modes/pseudo/manage.sh verify demo-001
```

`up` 最多等待 180 秒，检查两个服务存活、恰好 1 个 Live DataNode、安全模式关闭以及 HDFS 根目录可访问。失败保存并输出诊断，不因容器显示 Up 就判定成功。

预期 `status` 显示 NameNode、DataNode，`Live datanodes (1):`、`Safe mode is OFF`；默认作业显示实际词频、`RESULT_PASS distinct_words=2 total_words=3` 和 `job_local...`。访问 [NameNode Web](http://127.0.0.1:19870/) 查看节点，Web 页中容器内部名称仅供容器网络使用。

固定输入复用成员 5 的 `modes/standalone/input/sample.txt`。本次输入位于 HDFS `/project/input/member5/demo-001/sample.txt`，结果位于 `/project/output/member5/demo-001/`。已有输入或输出时拒绝重复运行；下一次使用 `demo-002` 等新 ID。

## 使用自己的文本

HDFS 已通过 up 启动后，使用 `run <run-id> [宿主机输入文件或目录]`。相对路径按当前目录解释，路径含空格/中文时加引号；不传路径仍使用默认样例。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\pseudo\manage.ps1 run own-001 "D:\data\my-text.txt"
powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\pseudo\manage.ps1 run own-002 "D:\data\my texts"
powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\pseudo\manage.ps1 verify own-001
```

```bash
bash modes/pseudo/manage.sh run own-001 "/path/to/my-text.txt"
bash modes/pseudo/manage.sh run own-002 "/path/to/my texts"
bash modes/pseudo/manage.sh verify own-001
```

输入规则与[单机模式](../standalone/README.md#使用自己的文本)相同：UTF-8 纯文本、支持 BOM/CRLF，目录不递归并忽略隐藏条目，按空白分词、区分大小写及标点。空文件生成空结果。终端打印实际词频和不同词数/总词数。

自定义输入只读挂载到临时 `client` 容器，由其上传到本次 HDFS 输入目录并执行本地 MapReduce；容器执行后自动移除，不重建或改动运行中的 HDFS 服务。常驻 HDFS 仍只有 1 个容器、1 个 DataNode；没有 YARN 或新增 Worker。客户端与服务使用本项目独立网络，不挂载 HDFS 数据卷，资源上限为 1 CPU/1 GiB；服务仍为 2 CPU/2 GiB。作业期间两者合计上限 3 CPU/3 GiB。

verify 从已保存的 HDFS 输入独立计算预期词频，再与实际输出比较，原始文件之后修改也不影响旧作业验证。目录内文件名保留；单文件上传后名为 `member5-input`，可在容器 shell 用 `hdfs dfs -ls /project/input/member5/own-001` 查看。

## 进入、重启、停止与恢复

Windows 将下表动作放到 `powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\pseudo\manage.ps1` 后；Mac 放到 `bash modes/pseudo/manage.sh` 后。

| 动作 | 行为 |
| --- | --- |
| `shell` | 进入服务容器；`exit` 返回电脑终端 |
| `restart` | 重启并重新等待就绪，保留数据 |
| `verify demo-001` | 重启后核对原作业结果 |
| `logs` | 查看最近 200 行服务日志 |
| `stop` | 停止，保留容器和卷 |
| `down` | 移除本项目容器和网络，保留卷 |
| `up` | 使用已有元数据恢复，不重新格式化 |
| `test` | 宿主机 Python 3 执行独立测试，不使用上述演示数据卷 |

例如，Windows 重建容器并核对结果：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\pseudo\manage.ps1 down
powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\pseudo\manage.ps1 up
powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\pseudo\manage.ps1 verify demo-001
```

在 `shell` 进入的**容器终端**可执行：

```bash
jps
hdfs dfsadmin -report
hdfs dfs -ls /project/input/member5/demo-001
hdfs dfs -cat /project/input/member5/demo-001/sample.txt
hdfs dfs -cat '/project/output/member5/demo-001/part-r-*'
```

## 初始化保护与资源边界

`init` 只用于新空目录；已有 NameNode `current/VERSION` 时保持原样。缺少该标记但 NameNode 或 DataNode 目录非空时拒绝格式化。运行期间拒绝 init；卷内文件锁也阻止跨容器的并发 init/start。正常启动、重启、停止不调用格式化。任何一个服务退出会终止另一服务，并让容器失败退出。

项目名 `hadoop-m5-pseudo`，主机名 `pseudo`，URI `hdfs://pseudo:9000`，副本数 1。数据卷由该 Compose 项目独占，挂载 `/var/lib/hadoop`；数据目录分别为其下 `hdfs/namenode` 和 `hdfs/datanode`。镜像用户 UID 1000，仓库及 XML 只读挂载，配置保留镜像其他默认文件。资源上限 2 CPU/2 GiB，两个服务 JVM 各限 256 MiB 堆。

只向宿主机发布 `127.0.0.1:19870:9870`，不发布 HDFS RPC/传输端口，也不使用公共 `master/worker` 网络或数据卷。公共 `.development` 中的三节点 URI 不会覆盖本模式的 XML。

端口被占用时明确失败，不停止占用程序。需要换端口可在当前宿主机终端设置 `M5_PSEUDO_WEB_PORT` 后启动，例如 PowerShell `$env:M5_PSEUDO_WEB_PORT='19871'` 或 Bash `export M5_PSEUDO_WEB_PORT=19871`，Web 地址相应调整；不修改公共文件。

日志：管理命令保存在 `runtime/member5/pseudo/control/`，服务日志用 `logs` 查看。运行失败不自动清理用户数据。管理入口没有删除演示数据卷的动作；`down` 保留数据。所有 Compose 命令均明确指定本模式配置、项目名和 `.development`。

run-id 只接受字母、数字、`-`、`_`；成功为 0，运行/验证失败为非零，参数错误为 2。本目录 `node.sh`、`healthcheck.sh`、`run.sh`、`verify.sh` 是容器内实现；PowerShell/Bash 宿主机入口复用成员 5 单机目录的辅助脚本，因此交付时保留整个仓库。

本模块测试放 [对应 tests/ 子目录](../../tests/pseudo/)；实验步骤、结果和交付链接放 [对应 docs/modules/ 子目录](../../docs/modules/standalone-pseudo/)。
