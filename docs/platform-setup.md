# 组员使用说明（Windows / Mac）

只做自己系统的第 1—8 步，再创建任务分支。一次执行一个代码框，报错先停下处理。电脑无需另装 Java 或 Hadoop。

[Windows](#windows) · [Mac](#mac) · [任务分支](#task-branch) · [每天使用](#daily)

## 这 8 步在做什么

| 步骤 | 作用 |
| --- | --- |
| 1. 准备 Git | 安装下载和管理项目代码的工具 |
| 2. 安装并启动 Docker | 让电脑能够运行统一的开发环境 |
| 3. 检查 Docker | 确认引擎已启动，能运行 Linux 容器 |
| 4. 下载项目 | 获取全组共用的代码、配置和脚本 |
| 5. 检查项目配置 | 确认 Docker 能正确识别项目的环境配置 |
| 6. 下载并导入镜像 | 使用组长准备好的 Java/Hadoop 环境，不必自己搭建 |
| 7. 验证环境 | 实际检查版本、编译和 Hadoop API 是否正常 |
| 8. 进入开发容器 | 进入统一环境，准备编译、运行和测试自己的模块 |

**最终目的：让每位成员在自己电脑上，用同一份项目代码和同一套 Java/Hadoop 环境开始开发，减少环境差异造成的联调问题。** 完成后创建自己的任务分支；这代表公共开发环境已就绪，三节点集群和具体应用还需对应成员实现。

<a id="windows"></a>
## Windows

### 第 1 步：准备 Git

从 [Git 官网](https://git-scm.com/downloads) 安装 Git，在开始菜单打开 PowerShell，执行：

```powershell
git --version
```

显示 git version 和版本号即可。安装后找不到命令，关闭 PowerShell 再打开。

### 第 2 步：安装并启动 Docker Desktop

按 [Docker Windows 安装说明](https://docs.docker.com/desktop/setup/install/windows-install/) 安装，使用 WSL2 后端和 Linux 容器；按提示重启后打开 Docker Desktop，等待引擎就绪。缺少 WSL 组件时看 [前置条件](windows-setup.md)。

### 第 3 步：检查 Docker

重新打开电脑终端，逐条执行：

```powershell
docker --version
docker compose version
docker info --format '{{.OSType}}'
```

前两条显示版本，第三条显示 linux 后继续。

### 第 4 步：下载项目

在电脑终端逐条执行：

```powershell
Set-Location "$HOME"
git clone --branch common/phase0-bootstrap https://github.com/deep-hang/hadoop.git
cd hadoop
```

项目保存在账户主目录的 hadoop 文件夹，后面称“项目根目录”。下载过就进入原目录，不重复克隆；目录已存在时不要删除覆盖。

### 第 5 步：检查项目配置

在电脑终端的项目根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 doctor
```

显示 Compose 版本、没有报错即可继续。

### 第 6 步：下载并导入镜像

点击 [下载镜像包（约 829 MB）](https://github.com/deep-hang/hadoop/releases/download/phase0-image-v0.1/hadoop-base-v0.1.tar.gz)，保存到当前账户的 Downloads（下载）文件夹，等下载完成，**不要解压**。然后在电脑终端执行：

```powershell
docker load --input "$HOME\Downloads\hadoop-base-v0.1.tar.gz"
```

看到 Loaded image: hadoop-base:v0.1 即成功。保存在其他位置时，把引号里的路径换成实际完整路径。

### 第 7 步：验证环境

在电脑终端的项目根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 verify
```

最后应显示：

```text
BASE_API_PASS
PASS: frozen Java/Hadoop versions, paths, compiler and Hadoop API loading
```

### 第 8 步：进入开发容器

仍在电脑终端的项目根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 shell
```

现在进入了容器终端，执行：

```bash
pwd
```

显示 /workspace 即正确，这是电脑上项目文件夹在容器内的位置。在这里保存的项目代码会保留。输入 exit 回到电脑终端，再创建下面的任务分支。

<a id="mac"></a>
## Mac（Intel / Apple M 系列）

### 第 1 步：准备 Git

按 Command + 空格，搜索并打开“终端”，执行：

```bash
git --version
```

显示 git version 和版本号即可。若提示安装命令行开发工具，按提示完成安装再试；仍缺少 Git 时按 [官方说明](https://git-scm.com/downloads/mac) 安装。

### 第 2 步：安装并启动 Docker Desktop

在苹果菜单 →“关于本机”查看芯片，再从 [Docker Mac 安装页](https://docs.docker.com/desktop/setup/install/mac-install/) 下载对应安装包：Intel 选 Mac with Intel chip；Apple M 系列选 Mac with Apple silicon。打开 .dmg，将 Docker 拖到“应用程序”，打开并完成首次提示，等待引擎就绪。

M 系列保持项目的 linux/amd64 设置，通过模拟运行，速度可能较慢。

### 第 3 步：检查 Docker

重新打开电脑终端，逐条执行：

```bash
docker --version
docker compose version
docker info --format '{{.OSType}}'
```

前两条显示版本，第三条显示 linux 后继续。

### 第 4 步：下载项目

在电脑终端逐条执行：

```bash
cd "$HOME"
git clone --branch common/phase0-bootstrap https://github.com/deep-hang/hadoop.git
cd hadoop
```

项目保存在账户主目录的 hadoop 文件夹，后面称“项目根目录”。下载过就进入原目录，不重复克隆；目录已存在时不要删除覆盖。

### 第 5 步：检查项目配置

在电脑终端的项目根目录执行：

```bash
bash scripts/dev.sh doctor
```

显示 Compose 版本、没有报错即可继续。

### 第 6 步：下载并导入镜像

点击 [下载镜像包（约 829 MB）](https://github.com/deep-hang/hadoop/releases/download/phase0-image-v0.1/hadoop-base-v0.1.tar.gz)，保存到当前账户的 Downloads（下载）文件夹，等下载完成，**不要解压**。然后在电脑终端执行：

```bash
docker load --input "$HOME/Downloads/hadoop-base-v0.1.tar.gz"
```

看到 Loaded image: hadoop-base:v0.1 即成功。保存在其他位置时，把引号里的路径换成实际完整路径。

### 第 7 步：验证环境

在电脑终端的项目根目录执行：

```bash
bash scripts/dev.sh verify
```

最后应显示：

```text
BASE_API_PASS
PASS: frozen Java/Hadoop versions, paths, compiler and Hadoop API loading
```

### 第 8 步：进入开发容器

仍在电脑终端的项目根目录执行：

```bash
bash scripts/dev.sh shell
```

现在进入了容器终端，执行：

```bash
pwd
```

显示 /workspace 即正确，这是电脑上项目文件夹在容器内的位置。在这里保存的项目代码会保留。输入 exit 回到电脑终端，再创建下面的任务分支。

<a id="task-branch"></a>
## 创建任务分支（首次做一次）

1. 确认已 exit 回电脑终端，且位于项目根目录。
2. 只执行自己任务对应的一条命令：

| 任务 | 命令 |
| --- | --- |
| 2 号 | `git switch -c feat/distributed` |
| 3 号 | `git switch -c feat/hdfs` |
| 4 号 | `git switch -c feat/yarn-mapreduce` |
| 5 号 | `git switch -c feat/standalone-pseudo` |
| 6 号 | `git switch -c feat/wordcount` |
| 7 号 | `git switch -c feat/mergefile` |

3. 执行 git branch --show-current，确认显示自己的 feat/... 分支，再按 [公共接口](interfaces.md) 开发。分支已存在时用 git switch 加实际分支名切换，不再加 -c。

<a id="daily"></a>
## 以后每天怎么开始

1. 打开 Docker Desktop，等待引擎就绪。
2. 打开电脑终端，按自己的系统执行下面命令，进入项目和开发容器。

Windows：

```powershell
Set-Location "$HOME\hadoop"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 shell
```

Mac：

```bash
cd "$HOME/hadoop"
bash scripts/dev.sh shell
```

3. 在电脑编辑器里修改项目文件，在容器的 /workspace 编译和测试本模块。
4. 结束时在容器输入 exit；回电脑终端按 [协作规则](contributing.md) 提交代码。无需重复下载或导入镜像。

当前开发容器不启动三节点集群；模块连接与交接看 [联调说明](member-onboarding.md)。

<a id="existing"></a>
<a id="troubleshooting"></a>
## 遇到问题

| 问题 | 怎么做 |
| --- | --- |
| 找不到 git / docker | 确认安装完成，关闭并重新打开终端 |
| 无法连接 Docker | 打开 Docker Desktop，等引擎就绪，再重试 |
| 镜像包找不到 | 确认下载完成，核对导入命令中的完整路径 |
| 找不到 hadoop-base:v0.1 / 拉取 denied | 先完成第 6 步导入，再验证 |
| 找不到 scripts 或 .development | 回到 hadoop 项目根目录执行 |
| Mac 挂载被拒绝 | 按 Docker 提示允许访问项目目录，再重试 |
| M 系列出现 exec format error | 确认装的是 Apple 芯片版 Docker，保留项目 linux/amd64 设置，检查 Docker 模拟支持 |
| 已有项目需要更新 | 在电脑终端检查 git status 和当前分支；仅当工作区干净且在 common/phase0-bootstrap 时执行 git pull --ff-only。有功能分支或本地修改时先保留，由组长协调更新 |

仍失败时，把步骤号、完整命令与报错发给组长，排错时再提供系统和芯片信息。底座已在组长 Windows 上实测，Mac 需按第 7 步完成本机验收。
