# 成员 5：统一操作与离线报告

增强入口需要 Python 3.10+ 和现有 Docker Linux 环境，只使用 Python 标准库。基础镜像仍为 `hadoop-base:v0.1`。原有 `manage.ps1` / `manage.sh` 保持原用法；启用本页功能需要显式使用 `console` 新入口。

## 启动菜单

在项目根目录的电脑终端执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\modes\standalone\console.ps1
```

Windows 也可双击 `modes/standalone/console.cmd`。Mac/Linux 或 Windows Git Bash：

```bash
bash modes/standalone/console.sh
```

入口支持从其他目录通过完整路径启动。输入相对路径以调用者当前目录为准；输入提示可以粘贴带双引号的路径。命令行路径包含空格或中文时加引号。非交互调用必须指定动作，不会等待菜单输入。

菜单包括环境检查、两种模式运行、双模式对照、历史与报告、HDFS 查看、伪分布式服务管理和打开 NameNode 页面。历史菜单能打开日志、单机输出目录、报告，以及执行真实结果复验。

## 首次核验顺序

1. 选择“检查运行环境”。
2. 选择“运行单机模式”，输入文件路径，或直接回车使用默认样例；ID 回车自动生成。
3. 菜单“管理伪分布式服务”中，首次执行 `init`，再执行 `up`。已有且运行中的服务直接使用。
4. 选择“同一输入对照两种模式”，使用同一文件或目录运行。
5. 查看终端摘要，打开生成的 HTML 报告。
6. 查看历史并重新验证；用 HDFS 菜单查看上传文件和 `part-r-00000` 等输出文件。
7. 演示结束可执行 `stop` 或 `down`；两者均不删除数据卷。

运行或对照命令不会隐式格式化、初始化、启动 HDFS。`up` 仍等待两个服务、一个 Live DataNode、安全模式关闭和根目录可访问。初始化失败请查看日志，不能通过删除元数据绕过保护。

本轮没有新增持久化演示菜单。原管理入口的 restart、停止恢复及持久化测试继续保留。

## 命令行接口

以下以 `python -B modes/standalone/console.py` 为入口；PowerShell/Bash 包装器接受相同参数。

```text
doctor
run standalone [--input PATH] [--id ID] [--verbose]
run pseudo [--input PATH] [--id ID] [--verbose]
compare [--input PATH] [--id ID] [--verbose]
history [--mode standalone|pseudo|compare] [--limit 20]
show standalone|pseudo|compare ID
verify standalone|pseudo ID
report standalone|pseudo|compare ID [--open]
hdfs ls [--area input|output] [--id ID]
hdfs cat input|output ID FILENAME
web
service init|up|status|logs|stop|down
```

例子：

```powershell
python -B modes/standalone/console.py doctor
python -B modes/standalone/console.py run standalone --input "runtime/member5/custom-input-example.txt"
python -B modes/standalone/console.py service init
python -B modes/standalone/console.py service up
python -B modes/standalone/console.py compare --input "runtime/member5/custom-input-example.txt"
python -B modes/standalone/console.py history
```

把结果中的实际 ID 用到后续命令。手动 ID 已存在会失败；不要反复使用同一个示例 ID。自动 ID 使用 UTC 时间与随机后缀，显示时间附带时区。成功返回 0，执行/核验失败返回 1，参数或输入校验错误返回 2，用户中断返回 130。

输入沿用原有 UTF-8 规则：支持 BOM、CRLF、中文，按空白分词，保留大小写与标点；目录不递归，忽略 `.`、`_` 开头条目；空文本允许，空目录、无效 UTF-8、压缩文件不接受。不提供中文自动分词或任意自定义算法。

## 运行记录与证据

增强记录位于 `runtime/member5/console/runs/<mode>/<id>/`，对照记录位于 `runtime/member5/console/comparisons/<id>/`。包含：

- `record.json`：版本化元数据、执行和验证状态、源码提交、工作区是否有未提交修改、镜像 ID。
- `input/`：提交前保存的输入副本；文件名、大小、SHA-256 写入元数据。
- `commands.log`：完整 Docker/Hadoop 输出；重新验证另建日志。
- `verification-*.json`：每次独立核验的结果与时间。
- `result.tsv`：完整词频，按计数降序、同频按文本排序。
- `reports/<版本>/`：独立 HTML、词频 TSV 和 JSON，可整体复制交接。

复制前后核对输入文件清单和内容哈希，发现变化就停止；作业读取副本。双模式由同一副本顺序运行，两边还需核对实际保存的输入哈希和完整词频，全部通过才显示“对照通过”。不使用结果的前 20 名代替完整验证。

配置取自实际 Hadoop JobConf，HDFS 节点状态来自实际文件系统连接。报告中的检测结果都有采集时间，不等于当前服务状态；端到端耗时包含初始化客户端、检查和读取等开销，不据此比较性能优劣。

运行、验证、报告分别保存状态。报告写入失败会使入口返回失败，但保留作业成功与验证通过的事实。中断只尝试停止拥有当前调用标签的临时客户端，不停止常驻 HDFS。运行中记录如遇电脑断电可能来不及更新，请结合日志和实际容器状态判断。

旧入口作业可通过历史发现并导入；未记录的时间、镜像等不补造。导入后运行状态仍为未知，真实复验通过会单独记录。HDFS 不可用时只显示已保存历史，并提示未能发现其他 HDFS 记录。

对照报告保存当时子作业的记录与完整结果副本；之后对单个作业复验或修改其结果不会重写历史对照结论。需要检查当前状态时分别运行两个 `verify` 命令。

## HDFS 快捷查看

快捷操作只访问 `/project/input/member5/` 和 `/project/output/member5/`。按运行 ID 和文件名选择，不接受路径跳转。文件信息通过 Hadoop FileSystem API 输出 JSON，支持中文、空格、`#`、`%` 等文件名。

文件预览最多读取 64 KiB、显示 200 行，达到上限时显示截断提示。这里没有删除、覆盖或任意 HDFS shell 命令。`web` 读取当前项目真实端口映射，支持已有 `M5_PSEUDO_WEB_PORT` 自定义端口。

## 离线报告

直接打开 `reports/<版本>/index.html`。页面不请求外部脚本、字体或网络服务，不占用新端口。报告展示运行状态、实测配置、输入哈希、词频前 20 名、搜索分页表及原始证据位置。

页面最多嵌入 5,000 条词频，搜索仅覆盖这部分；完整结果在旁边 TSV 中。总词数与核验使用全部结果。空输入显示 0 个词；失败报告可能没有可展示结果，以状态为准。用户文本、文件名和错误均转义显示。

每次生成报告新建版本目录，不覆盖旧版。复制完整报告目录可离线查看数据，原始绝对日志路径仍仅指向运行机器。浏览器无法打开时，终端仍会给出 HTML 完整路径，可手动打开。

## 常见情况

| 情况 | 处理 |
| --- | --- |
| Python 未安装或低于 3.10 | 安装兼容 Python；原有 manage 入口仍可用于基础运行 |
| Docker 未启动 | 启动 Docker Desktop Linux 引擎，运行 doctor |
| 伪分布式未就绪 | service status/logs；首次显式 init，再 up |
| ID 已存在 | 使用自动 ID 或另一个手动 ID，原结果保持不变 |
| 输入复制期间变化 | 停止修改源文件，使用新 ID 重试 |
| 验证失败 | 查本次 verify 日志和 JSON，不用历史成功覆盖当前失败 |
| 报告无法写入 | 检查磁盘与路径权限，已有作业数据保留，之后用 report 重试 |
| HTML 浏览器视觉效果未验 | 核对验收记录的已测/未测范围，再手动打开报告 |

## 开发与团队边界

新 Python 编排共用原有容器运行/验证脚本，使用原 Compose 项目、网络、卷、端口和资源限制。正常运行只操作成员 5，测试使用随机项目。模块入口没有全局 Docker 清理或删除演示数据卷动作。

只在成员 5 五个目录增加实现、测试和文档，生成物位于已忽略的 runtime。原公共及其他成员文件不变。当前只保存本地提交，必须经用户核验同意后才推送分支或创建 PR。
