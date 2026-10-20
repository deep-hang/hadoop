# 不同系统使用说明：按编号操作

第一次使用只做自己系统的第 1—8 步，再创建任务分支。以后每天使用看文末“每天怎么开始”，不用重新安装。无需提前向组长登记系统或处理器。

| 电脑 | 点击对应步骤 | 使用窗口 |
| --- | --- | --- |
| Windows（Intel/AMD） | [Windows](#windows) | PowerShell |
| Intel Mac | [Intel Mac](#mac-intel) | 终端 Terminal |
| Apple M 系列 Mac | [M 系列 Mac](#mac-apple) | 终端 Terminal |
| Linux | [Linux](#linux) | Bash 终端 |

## 开始前先看

Mac 和 Linux 的安装步骤引用官方文档，不同版本的界面文字可能略有差别；判断 Docker 是否可用，以各系统第 3 步的实际检查结果为准。

1. 一次复制一个代码框，逐条执行，等上一条结束再做下一条；报错时先处理，不继续往下跑。
2. “电脑终端”指 PowerShell 或 Mac/Linux 终端；执行 shell 后进入的是“容器终端”。下文会标明位置。
3. Git 用来下载和保存代码，Docker 提供统一环境。电脑本身不必另外安装 Java、Hadoop 或 Linux 虚拟机。
4. 本文验收公共底座，通过后开始自己的模块；三节点集群与应用还需对应成员实现。

<a id="windows"></a>
## Windows（Intel/AMD）

### 第 1 步：准备 Git，打开电脑终端

从 [Git 官方下载页](https://git-scm.com/downloads) 选择 Windows 安装包并安装。在开始菜单搜索 PowerShell 并打开。

执行以下命令检查 Git：

```powershell
git --version
```

看到 git version 和版本号即可继续，已经安装的人不用重装。若找不到命令，安装完成后关闭 PowerShell，重新打开再试。

### 第 2 步：安装并启动 Docker

1. 打开 [Docker 官方 Windows 安装页](https://docs.docker.com/desktop/setup/install/windows-install/)，核对系统要求，下载并安装 Docker Desktop。
2. 按安装提示准备 WSL2 与虚拟机平台。缺少组件时按 [Windows 前置条件](windows-setup.md) 处理，要求重启时先保存文件并重启。
3. 启动 Docker Desktop，完成首次运行提示，使用 WSL2 后端及 Linux 容器，等待引擎运行成功。
4. 关闭旧 PowerShell，重新打开普通 PowerShell；后续项目命令不需要管理员窗口。

### 第 3 步：确认 Docker 真正可用

在电脑终端逐条执行：

```powershell
docker --version
docker compose version
docker info --format '{{.OSType}}'
```

前两条分别显示 Docker、Compose 的版本；第三条应显示 linux。出现找不到命令、无法连接引擎、权限错误时，先看 [报错自查](#troubleshooting)，处理好再继续。

### 第 4 步：下载项目，进入项目根目录

第一次下载的人在电脑终端逐条执行：

```powershell
Set-Location "$HOME"
git clone --branch common/phase0-bootstrap https://github.com/deep-hang/hadoop.git
cd hadoop
Get-ChildItem -Force
```

项目现在位于当前账户主目录下的 hadoop 文件夹。最后应看到 README.md、scripts、compose、.development 等文件或目录；这就是下文的“项目根目录”。

如果提示 hadoop 文件夹已存在，不删除、不在里面再次克隆，先看 [已有项目怎么办](#existing)。正确下载过的人不重复克隆。

### 第 5 步：检查项目配置

保持在电脑终端的项目根目录，执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 doctor
```

成功时显示 Compose 版本并返回可输入命令的提示符，不一定出现 PASS。紧接着单独执行：

```powershell
$LASTEXITCODE
```

结果为 0 表示成功；不是 0 或出现错误时先修复再继续。

### 第 6 步：获取统一镜像（A、B 只选一种）

**A：从 GitHub 下载已验证镜像（推荐）。**

1. 点击 [下载 hadoop-base-v0.1.tar.gz](https://github.com/deep-hang/hadoop/releases/download/phase0-image-v0.1/hadoop-base-v0.1.tar.gz)，将文件保存到当前账户的 Downloads（下载）文件夹。文件约 829 MB，等待浏览器显示下载完成，不要解压。
2. 如直链不便使用，打开 [镜像发布页](https://github.com/deep-hang/hadoop/releases/tag/phase0-image-v0.1)，展开 Assets，点击 hadoop-base-v0.1.tar.gz；Source code 是源码压缩包，不能代替镜像。
3. 保持在电脑终端，执行下面的导入命令：

```powershell
docker load --input "$HOME\Downloads\hadoop-base-v0.1.tar.gz"
```

保存位置不同时，把引号中的路径换成实际完整路径。成功时看到 Loaded image: hadoop-base:v0.1。完成 A 后跳过 B，执行本步末尾的镜像检查，再做第 7 步。

**B：没有镜像包，自行构建。** 在电脑终端的项目根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 build
```

首次会下载基础镜像和 Hadoop，需要等待。结束后立即单独执行：

```powershell
$LASTEXITCODE
```

结果为 0 才继续；失败时按 [镜像与缓存说明](../docker/README.md) 处理后重试。镜像包作为 GitHub Release 附件提供，不在 Git 源码历史里；克隆代码不等于下载镜像。

A 或 B 完成后，都执行以下命令检查镜像存在：

```powershell
docker image inspect hadoop-base:v0.1 --format '{{.Os}}/{{.Architecture}}'
```

应显示 linux/amd64。提示镜像不存在时，先完成导入或构建，不直接运行 verify。

### 第 7 步：验收 Java/Hadoop 底座

在电脑终端的项目根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 verify
```

最后应看到：

```text
BASE_API_PASS
PASS: frozen Java/Hadoop versions, paths, compiler and Hadoop API loading
```

看到这两行且命令成功结束，才算本机基础验收通过。失败时先按文末报错自查处理，不另外装一套本机 Hadoop 替代验收。

### 第 8 步：进入开发容器，检查后退出

在电脑终端的项目根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 shell
```

成功后进入 Linux 容器。下面的命令改在**容器终端内**逐条执行：

```bash
pwd
java -version
hadoop version
ls
```

预期：pwd 显示 /workspace，Java 版本含 1.8.0_442，Hadoop 显示 Hadoop 3.3.6，ls 能看到项目文件。

/workspace 对应电脑上的 hadoop 项目目录，在这里保存的代码会写回电脑文件夹；不要仅把源码放在容器其他临时目录。检查后在容器内执行：

```bash
exit
```

现在回到电脑终端，继续 [创建自己的任务分支](#task-branch)。

<a id="mac-intel"></a>
## Intel Mac

### 第 1 步：准备 Git，打开电脑终端

点击苹果菜单 →“关于本机”，确认是 Intel 处理器。如果不是，请返回顶部选择正确系统。按 Command + 空格，搜索“终端”或 Terminal 并打开。

执行以下命令检查 Git：

```bash
git --version
```

看到 git version 和版本号即可继续，已经安装的人不用重装。若系统提示安装命令行开发工具，完成安装后重试；仍找不到 Git 时按 [Git 官方 macOS 安装说明](https://git-scm.com/downloads/mac) 安装。

### 第 2 步：安装并启动 Docker

1. 打开 [Docker 官方 Mac 安装页](https://docs.docker.com/desktop/setup/install/mac-install/)，下载 **Mac with Intel chip** 对应的安装包。
2. 打开下载的 .dmg，把 Docker 拖到“应用程序”。
3. 从“应用程序”打开 Docker，完成首次运行提示和系统要求的授权，等待引擎运行成功。
4. 重新打开终端；Mac 不执行 Windows 的 WSL 命令或 .ps1 脚本。

### 第 3 步：确认 Docker 真正可用

在电脑终端逐条执行：

```bash
docker --version
docker compose version
docker info --format '{{.OSType}}'
```

前两条分别显示 Docker、Compose 的版本；第三条应显示 linux。出现找不到命令、无法连接引擎、权限错误时，先看 [报错自查](#troubleshooting)，处理好再继续。

### 第 4 步：下载项目，进入项目根目录

第一次下载的人在电脑终端逐条执行：

```bash
cd "$HOME"
git clone --branch common/phase0-bootstrap https://github.com/deep-hang/hadoop.git
cd hadoop
ls -a
```

项目现在位于当前账户主目录下的 hadoop 文件夹。最后应看到 README.md、scripts、compose、.development 等文件或目录；这就是下文的“项目根目录”。

如果提示 hadoop 文件夹已存在，不删除、不在里面再次克隆，先看 [已有项目怎么办](#existing)。正确下载过的人不重复克隆。

### 第 5 步：检查项目配置

保持在电脑终端的项目根目录，执行：

```bash
bash scripts/dev.sh doctor
```

成功时显示 Compose 版本并返回可输入命令的提示符，不一定出现 PASS。紧接着单独执行：

```bash
echo $?
```

结果为 0 表示成功；不是 0 或出现错误时先修复再继续。

### 第 6 步：获取统一镜像（A、B 只选一种）

**A：从 GitHub 下载已验证镜像（推荐）。**

1. 点击 [下载 hadoop-base-v0.1.tar.gz](https://github.com/deep-hang/hadoop/releases/download/phase0-image-v0.1/hadoop-base-v0.1.tar.gz)，将文件保存到当前账户的 Downloads（下载）文件夹。文件约 829 MB，等待浏览器显示下载完成，不要解压。
2. 如直链不便使用，打开 [镜像发布页](https://github.com/deep-hang/hadoop/releases/tag/phase0-image-v0.1)，展开 Assets，点击 hadoop-base-v0.1.tar.gz；Source code 是源码压缩包，不能代替镜像。
3. 保持在电脑终端，执行下面的导入命令：

```bash
docker load --input "$HOME/Downloads/hadoop-base-v0.1.tar.gz"
```

保存位置不同时，把引号中的路径换成实际完整路径。成功时看到 Loaded image: hadoop-base:v0.1。完成 A 后跳过 B，执行本步末尾的镜像检查，再做第 7 步。

**B：没有镜像包，自行构建。** 在电脑终端的项目根目录执行：

```bash
bash scripts/dev.sh build
```

首次会下载基础镜像和 Hadoop，需要等待。结束后立即单独执行：

```bash
echo $?
```

结果为 0 才继续；失败时按 [镜像与缓存说明](../docker/README.md) 处理后重试。镜像包作为 GitHub Release 附件提供，不在 Git 源码历史里；克隆代码不等于下载镜像。

A 或 B 完成后，都执行以下命令检查镜像存在：

```bash
docker image inspect hadoop-base:v0.1 --format '{{.Os}}/{{.Architecture}}'
```

应显示 linux/amd64。提示镜像不存在时，先完成导入或构建，不直接运行 verify。

### 第 7 步：验收 Java/Hadoop 底座

在电脑终端的项目根目录执行：

```bash
bash scripts/dev.sh verify
```

最后应看到：

```text
BASE_API_PASS
PASS: frozen Java/Hadoop versions, paths, compiler and Hadoop API loading
```

看到这两行且命令成功结束，才算本机基础验收通过。失败时先按文末报错自查处理，不另外装一套本机 Hadoop 替代验收。

### 第 8 步：进入开发容器，检查后退出

在电脑终端的项目根目录执行：

```bash
bash scripts/dev.sh shell
```

成功后进入 Linux 容器。下面的命令改在**容器终端内**逐条执行：

```bash
pwd
java -version
hadoop version
ls
```

预期：pwd 显示 /workspace，Java 版本含 1.8.0_442，Hadoop 显示 Hadoop 3.3.6，ls 能看到项目文件。

/workspace 对应电脑上的 hadoop 项目目录，在这里保存的代码会写回电脑文件夹；不要仅把源码放在容器其他临时目录。检查后在容器内执行：

```bash
exit
```

现在回到电脑终端，继续 [创建自己的任务分支](#task-branch)。

<a id="mac-apple"></a>
## Apple 芯片 Mac（M 系列）

### 第 1 步：准备 Git，打开电脑终端

点击苹果菜单 →“关于本机”，确认是 Apple M1、M2 或其他 M 系列芯片。如果不是，请返回顶部选择正确系统。按 Command + 空格，搜索“终端”或 Terminal 并打开。

执行以下命令检查 Git：

```bash
git --version
```

看到 git version 和版本号即可继续，已经安装的人不用重装。若系统提示安装命令行开发工具，完成安装后重试；仍找不到 Git 时按 [Git 官方 macOS 安装说明](https://git-scm.com/downloads/mac) 安装。

### 第 2 步：安装并启动 Docker

1. 打开 [Docker 官方 Mac 安装页](https://docs.docker.com/desktop/setup/install/mac-install/)，下载 **Mac with Apple silicon** 对应的安装包。
2. 打开下载的 .dmg，把 Docker 拖到“应用程序”。
3. 从“应用程序”打开 Docker，完成首次运行提示和系统要求的授权，等待引擎运行成功。
4. 重新打开终端；Mac 不执行 Windows 的 WSL 命令或 .ps1 脚本。

Docker 软件选择 Apple 芯片版，项目容器仍使用 linux/amd64。保持 Compose 的 platform 设置，不自行改成 arm64 或更换 Java/Hadoop。Docker Desktop 提供架构模拟支持，编译和运行可能较慢，见 [官方模拟说明](https://docs.docker.com/build/building/multi-platform/)。

### 第 3 步：确认 Docker 真正可用

在电脑终端逐条执行：

```bash
docker --version
docker compose version
docker info --format '{{.OSType}}'
```

前两条分别显示 Docker、Compose 的版本；第三条应显示 linux。出现找不到命令、无法连接引擎、权限错误时，先看 [报错自查](#troubleshooting)，处理好再继续。

### 第 4 步：下载项目，进入项目根目录

第一次下载的人在电脑终端逐条执行：

```bash
cd "$HOME"
git clone --branch common/phase0-bootstrap https://github.com/deep-hang/hadoop.git
cd hadoop
ls -a
```

项目现在位于当前账户主目录下的 hadoop 文件夹。最后应看到 README.md、scripts、compose、.development 等文件或目录；这就是下文的“项目根目录”。

如果提示 hadoop 文件夹已存在，不删除、不在里面再次克隆，先看 [已有项目怎么办](#existing)。正确下载过的人不重复克隆。

### 第 5 步：检查项目配置

保持在电脑终端的项目根目录，执行：

```bash
bash scripts/dev.sh doctor
```

成功时显示 Compose 版本并返回可输入命令的提示符，不一定出现 PASS。紧接着单独执行：

```bash
echo $?
```

结果为 0 表示成功；不是 0 或出现错误时先修复再继续。

### 第 6 步：获取统一镜像（A、B 只选一种）

**A：从 GitHub 下载已验证镜像（推荐）。**

1. 点击 [下载 hadoop-base-v0.1.tar.gz](https://github.com/deep-hang/hadoop/releases/download/phase0-image-v0.1/hadoop-base-v0.1.tar.gz)，将文件保存到当前账户的 Downloads（下载）文件夹。文件约 829 MB，等待浏览器显示下载完成，不要解压。
2. 如直链不便使用，打开 [镜像发布页](https://github.com/deep-hang/hadoop/releases/tag/phase0-image-v0.1)，展开 Assets，点击 hadoop-base-v0.1.tar.gz；Source code 是源码压缩包，不能代替镜像。
3. 保持在电脑终端，执行下面的导入命令：

```bash
docker load --input "$HOME/Downloads/hadoop-base-v0.1.tar.gz"
```

保存位置不同时，把引号中的路径换成实际完整路径。成功时看到 Loaded image: hadoop-base:v0.1。完成 A 后跳过 B，执行本步末尾的镜像检查，再做第 7 步。

**B：没有镜像包，自行构建。** 在电脑终端的项目根目录执行：

```bash
bash scripts/dev.sh build
```

首次会下载基础镜像和 Hadoop，需要等待。结束后立即单独执行：

```bash
echo $?
```

结果为 0 才继续；失败时按 [镜像与缓存说明](../docker/README.md) 处理后重试。镜像包作为 GitHub Release 附件提供，不在 Git 源码历史里；克隆代码不等于下载镜像。

A 或 B 完成后，都执行以下命令检查镜像存在：

```bash
docker image inspect hadoop-base:v0.1 --format '{{.Os}}/{{.Architecture}}'
```

应显示 linux/amd64。提示镜像不存在时，先完成导入或构建，不直接运行 verify。

### 第 7 步：验收 Java/Hadoop 底座

在电脑终端的项目根目录执行：

```bash
bash scripts/dev.sh verify
```

最后应看到：

```text
BASE_API_PASS
PASS: frozen Java/Hadoop versions, paths, compiler and Hadoop API loading
```

看到这两行且命令成功结束，才算本机基础验收通过。失败时先按文末报错自查处理，不另外装一套本机 Hadoop 替代验收。

### 第 8 步：进入开发容器，检查后退出

在电脑终端的项目根目录执行：

```bash
bash scripts/dev.sh shell
```

成功后进入 Linux 容器。下面的命令改在**容器终端内**逐条执行：

```bash
pwd
java -version
hadoop version
ls
```

预期：pwd 显示 /workspace，Java 版本含 1.8.0_442，Hadoop 显示 Hadoop 3.3.6，ls 能看到项目文件。

/workspace 对应电脑上的 hadoop 项目目录，在这里保存的代码会写回电脑文件夹；不要仅把源码放在容器其他临时目录。检查后在容器内执行：

```bash
exit
```

现在回到电脑终端，继续 [创建自己的任务分支](#task-branch)。

<a id="linux"></a>
## Linux

### 第 1 步：准备 Git，打开电脑终端

打开系统终端。

执行以下命令检查 Git：

```bash
git --version
```

看到 git version 和版本号即可继续，已经安装的人不用重装。若找不到命令，按 [Git 官方 Linux 安装说明](https://git-scm.com/downloads/linux) 选择自己的发行版安装，再检查。

### 第 2 步：安装并启动 Docker

1. 打开 [Docker Engine 官方安装入口](https://docs.docker.com/engine/install/)，选择自己的发行版，按对应页面安装并启动服务，不复制其他发行版的安装命令。
2. 按 [Compose 插件安装说明](https://docs.docker.com/compose/install/linux/) 安装插件。项目使用带空格的 docker compose。
3. 按 [Linux 安装后步骤](https://docs.docker.com/engine/install/linux-postinstall/) 配置当前用户的 Docker 权限；修改用户组后退出登录再重新登录。
4. 已有可用 Docker Desktop 的人也可继续使用。项目脚本使用当前用户，不给所有项目命令加 sudo 绕过权限问题。

检查处理器架构：

```bash
uname -m
```

x86_64 与当前镜像匹配；aarch64 或 arm64 需要先按 [官方模拟说明](https://docs.docker.com/build/building/multi-platform/) 配置架构模拟，不自行更换公共镜像架构。

### 第 3 步：确认 Docker 真正可用

在电脑终端逐条执行：

```bash
docker --version
docker compose version
docker info --format '{{.OSType}}'
```

前两条分别显示 Docker、Compose 的版本；第三条应显示 linux。出现找不到命令、无法连接引擎、权限错误时，先看 [报错自查](#troubleshooting)，处理好再继续。

### 第 4 步：下载项目，进入项目根目录

第一次下载的人在电脑终端逐条执行：

```bash
cd "$HOME"
git clone --branch common/phase0-bootstrap https://github.com/deep-hang/hadoop.git
cd hadoop
ls -a
```

项目现在位于当前账户主目录下的 hadoop 文件夹。最后应看到 README.md、scripts、compose、.development 等文件或目录；这就是下文的“项目根目录”。

如果提示 hadoop 文件夹已存在，不删除、不在里面再次克隆，先看 [已有项目怎么办](#existing)。正确下载过的人不重复克隆。

### 第 5 步：检查项目配置

保持在电脑终端的项目根目录，执行：

```bash
bash scripts/dev.sh doctor
```

成功时显示 Compose 版本并返回可输入命令的提示符，不一定出现 PASS。紧接着单独执行：

```bash
echo $?
```

结果为 0 表示成功；不是 0 或出现错误时先修复再继续。

### 第 6 步：获取统一镜像（A、B 只选一种）

**A：从 GitHub 下载已验证镜像（推荐）。**

1. 点击 [下载 hadoop-base-v0.1.tar.gz](https://github.com/deep-hang/hadoop/releases/download/phase0-image-v0.1/hadoop-base-v0.1.tar.gz)，将文件保存到当前账户的 Downloads（下载）文件夹。文件约 829 MB，等待浏览器显示下载完成，不要解压。
2. 如直链不便使用，打开 [镜像发布页](https://github.com/deep-hang/hadoop/releases/tag/phase0-image-v0.1)，展开 Assets，点击 hadoop-base-v0.1.tar.gz；Source code 是源码压缩包，不能代替镜像。
3. 保持在电脑终端，执行下面的导入命令：

```bash
docker load --input "$HOME/Downloads/hadoop-base-v0.1.tar.gz"
```

保存位置不同时，把引号中的路径换成实际完整路径。成功时看到 Loaded image: hadoop-base:v0.1。完成 A 后跳过 B，执行本步末尾的镜像检查，再做第 7 步。

**B：没有镜像包，自行构建。** 在电脑终端的项目根目录执行：

```bash
bash scripts/dev.sh build
```

首次会下载基础镜像和 Hadoop，需要等待。结束后立即单独执行：

```bash
echo $?
```

结果为 0 才继续；失败时按 [镜像与缓存说明](../docker/README.md) 处理后重试。镜像包作为 GitHub Release 附件提供，不在 Git 源码历史里；克隆代码不等于下载镜像。

A 或 B 完成后，都执行以下命令检查镜像存在：

```bash
docker image inspect hadoop-base:v0.1 --format '{{.Os}}/{{.Architecture}}'
```

应显示 linux/amd64。提示镜像不存在时，先完成导入或构建，不直接运行 verify。

### 第 7 步：验收 Java/Hadoop 底座

在电脑终端的项目根目录执行：

```bash
bash scripts/dev.sh verify
```

最后应看到：

```text
BASE_API_PASS
PASS: frozen Java/Hadoop versions, paths, compiler and Hadoop API loading
```

看到这两行且命令成功结束，才算本机基础验收通过。失败时先按文末报错自查处理，不另外装一套本机 Hadoop 替代验收。

### 第 8 步：进入开发容器，检查后退出

在电脑终端的项目根目录执行：

```bash
bash scripts/dev.sh shell
```

成功后进入 Linux 容器。下面的命令改在**容器终端内**逐条执行：

```bash
pwd
java -version
hadoop version
ls
```

预期：pwd 显示 /workspace，Java 版本含 1.8.0_442，Hadoop 显示 Hadoop 3.3.6，ls 能看到项目文件。

/workspace 对应电脑上的 hadoop 项目目录，在这里保存的代码会写回电脑文件夹；不要仅把源码放在容器其他临时目录。检查后在容器内执行：

```bash
exit
```

现在回到电脑终端，继续 [创建自己的任务分支](#task-branch)。

<a id="task-branch"></a>
## 首次验收后：创建自己的任务分支

### 第 1 步：确认已退出容器，检查项目状态

Git 操作在电脑终端的项目根目录进行，仍在容器里就先输入 exit。

```text
git status
git branch --show-current
```

刚克隆时应在 common/phase0-bootstrap 分支且工作区干净。有本地改动先保存并确认用途，不删除或重置；已在自己的功能分支则不重复创建。

### 第 2 步：只执行自己任务对应的一条命令

| 任务号 | 创建并切换到自己的分支 |
| --- | --- |
| 2 号 | `git switch -c feat/distributed` |
| 3 号 | `git switch -c feat/hdfs` |
| 4 号 | `git switch -c feat/yarn-mapreduce` |
| 5 号 | `git switch -c feat/standalone-pseudo` |
| 6 号 | `git switch -c feat/wordcount` |
| 7 号 | `git switch -c feat/mergefile` |

不要执行全部六条。若分支已存在，运行 git branch 查看，确认后用 git switch 加实际分支名切换，不加 -c。

### 第 3 步：确认分支，阅读任务要求

```text
git branch --show-current
```

应显示自己的 feat/... 分支。然后阅读 [目录与负责人](../README.md#目录与负责人)、[公共接口](interfaces.md) 与 [成员联调验收](member-onboarding.md)，再修改自己的模块。

这里只创建本地分支，不自动上传代码。提交、推送与交接遵循 [协作规则](contributing.md)，公共文件修改先由组长协调。

<a id="daily"></a>
## 以后每天怎么开始

### 第 1 步：启动 Docker

Windows/Mac 打开 Docker Desktop 等引擎就绪；Linux 确认 Docker 服务运行。

### 第 2 步：打开电脑终端，回到项目根目录

按本文首次下载的人使用对应命令，放在其他目录时换成实际路径。

Windows PowerShell：

```powershell
Set-Location "$HOME\hadoop"
git branch --show-current
git status
```

Mac/Linux：

```bash
cd "$HOME/hadoop"
git branch --show-current
git status
```

确认在自己的功能分支；保留已有修改，不删除项目或重置分支。需要同步公共更新时按组长的集成安排处理。

### 第 3 步：进入容器开发

Windows PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 shell
```

Mac/Linux：

```bash
bash scripts/dev.sh shell
```

在电脑编辑器中打开项目文件夹编辑，在容器的 /workspace 里执行模块编译、运行、测试命令。基础镜像不变时，不必每天导入或 build。

### 第 4 步：结束当天工作

在容器内输入 exit 回电脑终端，再执行 git status 查看变化，按协作规则提交自己的修改。容器退出后会被移除，挂载的项目代码保留在电脑上。

目前 shell 不启动三节点集群。集群启动、提交应用与停止步骤由 2—4 号成员后续交付，按 [联调验收](member-onboarding.md) 衔接。

<a id="existing"></a>
## 已下载过项目怎么办

1. 在电脑终端进入原 hadoop 文件夹，不再 git clone。
2. 执行 git remote -v，确认 origin 指向 https://github.com/deep-hang/hadoop.git 或同一仓库的 SSH 地址。
3. 执行 git status 和 git branch --show-current。只有工作区干净且当前为 common/phase0-bootstrap 时，才执行下面的更新命令，然后从自己系统第 5 步继续：

```text
git pull --ff-only origin common/phase0-bootstrap
```

4. 已在功能分支开发或存在未提交修改时，保留原状，不覆盖、不重复克隆进此目录；先按协作规则保存工作，公共更新由组长协调接入。

<a id="troubleshooting"></a>
## 按报错自查

停在报错步骤，修复后重做该步，通过再继续，不需要从头重装。

| 报错或现象 | 处理顺序 |
| --- | --- |
| 找不到 git / docker | ①确认软件安装完成；②关掉并重开终端；③重跑版本检查 |
| 无法连接 daemon / pipe / socket | ①Windows/Mac 启动 Docker 等引擎就绪，Linux 检查服务；②Linux socket 权限错误按官方安装后步骤配置并重新登录；③重跑第 3 步 |
| Windows 第 3 步输出 windows | ①Docker Desktop 切换为 Linux 容器；②等引擎就绪；③重跑第 3 步 |
| hadoop 文件夹已存在 | ①不要删除；②按“已下载过项目怎么办”核对；③使用正确的原项目 |
| 找不到 scripts 或 .development | ①确认在电脑终端；②进入 hadoop 根目录；③确认能看到 README.md、scripts、compose；④重试 |
| docker load 找不到文件 | ①确认镜像下载完成且未解压；②核对文件名和位置；③换成真实完整路径并保留引号；④重试 |
| 找不到 hadoop-base:v0.1 / 拉取 denied | ①该镜像尚未发布到公共镜像仓库；②完成第 6 步导入或构建；③检查镜像存在后重跑 verify |
| build 下载超时 | ①检查网络和 Docker 代理；②参考镜像与缓存说明；③重试 build，通过再 verify |
| Mac 挂载目录被拒绝 | ①允许 Docker 访问项目目录，必要时在文件共享设置中授权；②重试 shell 或 verify |
| M 系列 / ARM Linux 出现 exec format error | ①使用项目脚本并保留 linux/amd64；②M 系列确认安装 Apple 芯片版 Docker；③按官方模拟说明排查；④重试 verify |
| M 系列运行较慢 | ①等待命令完成，不反复重复启动；②保留公共平台和版本；③基础通过后集群仍要单独验收 |
| Linux 容器写文件 Permission denied | ①exit 回电脑终端；②项目根目录执行 id -u 和 ls -ld .；③镜像用户 UID 为 1000，按账户情况协调目录写权限或用户映射；④不将整个仓库改成所有人可写 |
| CRLF / bad interpreter | ①确认用 Git 克隆；②编辑器中将脚本保存为 LF 换行；③重试，仓库已有 .gitattributes 约定 |

自查后仍失败时，发“停在第几步、完整命令、完整报错、系统和芯片信息”给组长。只在排错时提供这些信息，不需要提前登记系统。

实际测试过的是组长的 Windows 11 / Intel 电脑及其 Linux 容器；Mac 和其他 Linux 宿主机需按上面流程自行验收，不标记为已实机测试。
