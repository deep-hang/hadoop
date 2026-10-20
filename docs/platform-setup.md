# 按自己的系统开始使用

直接选择下面对应的系统操作，无需提前向组长登记系统或处理器。各系统使用同一份项目代码、`hadoop-base:v0.1` 镜像和公共接口；每人在自己的电脑通过基础验证后即可开始本模块开发。

| 电脑 | 阅读位置 | 使用的终端 |
| --- | --- | --- |
| Windows（Intel/AMD） | [Windows](#windows) | PowerShell |
| Intel Mac | [Intel Mac](#mac-intel) | 终端 Terminal |
| M1/M2/M3 等 Apple 芯片 Mac | [Apple 芯片 Mac](#mac-apple) | 终端 Terminal |
| Linux | [Linux](#linux) | Bash 终端 |

先安装 Git；可运行 `git --version` 检查，缺少时从 [Git 官方下载页](https://git-scm.com/downloads) 选择自己的系统。Java、Hadoop 和编译环境统一在容器里提供，宿主机无需另装。

## Windows

1. 按 [项目 Windows 安装说明](windows-setup.md) 准备 WSL2、虚拟机平台与 Docker Desktop，按系统提示重启。
2. 打开 Docker Desktop，使用 Linux 容器，等待引擎运行。
3. 打开 PowerShell，执行：

```powershell
git clone --branch common/phase0-bootstrap https://github.com/deep-hang/hadoop.git
cd hadoop
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 doctor
```

4. 按下文 [获取镜像](#image) 选择导入镜像包或自行构建，然后在项目根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 verify
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 shell
```

`verify` 用于验收，`shell` 用于进入开发容器。退出容器时输入 `exit`。这些命令不会修改 Windows 的永久执行策略。

<a id="mac-intel"></a>
## Intel Mac

1. 点左上角苹果菜单 →“关于本机”，确认显示 Intel 处理器。
2. 从 [Docker 官方 Mac 安装页](https://docs.docker.com/desktop/setup/install/mac-install/) 选择 **Mac with Intel chip**，安装 Docker Desktop。
3. 从“应用程序”打开 Docker，完成首次运行提示，等待引擎就绪。
4. 打开“终端”，执行：

```bash
git clone --branch common/phase0-bootstrap https://github.com/deep-hang/hadoop.git
cd hadoop
bash scripts/dev.sh doctor
```

5. 按下文 [获取镜像](#image) 导入镜像包或自行构建，然后在项目根目录执行：

```bash
bash scripts/dev.sh verify
bash scripts/dev.sh shell
```

容器内退出方式为 `exit`。Mac 上使用 Bash 入口即可，无需运行 PowerShell 脚本或 Windows 的 WSL 准备脚本。

<a id="mac-apple"></a>
## Apple 芯片 Mac（M 系列）

1. 在苹果菜单 →“关于本机”查看“芯片”，例如 Apple M1、M2 或其他 M 系列。
2. 从 [Docker 官方 Mac 安装页](https://docs.docker.com/desktop/setup/install/mac-install/) 选择 **Mac with Apple silicon**。Docker Desktop 安装包选择 Apple 芯片版本；项目容器仍按仓库约定使用 `linux/amd64`。
3. 打开 Docker，等待引擎就绪；在“终端”执行与 Intel Mac 相同的克隆、doctor、镜像导入或构建、verify、shell 命令。

项目已经在 Compose 中指定 `platform: linux/amd64`，保持这一设置即可。Docker Desktop 提供非本机架构的模拟支持，因此无需把项目改成 arm64 或更换 Java/Hadoop 版本。模拟运行可能使编译、启动和后续三节点实验变慢，见 [Docker 官方模拟说明](https://docs.docker.com/build/building/multi-platform/)。

基础 verify 通过后可开始开发；负责集群的成员在三节点模块完成后还要跑集群验收。如果遇到 `exec format error`，先检查 Docker Desktop 是否为 Apple 芯片版本且已更新、确认通过项目脚本运行并保留 Compose 的平台设置，再参考官方模拟说明排查。

## Linux

1. 安装适合自己发行版的 Docker Engine 和 Docker Compose 插件，见 [Docker Engine 官方安装入口](https://docs.docker.com/engine/install/) 及 [Compose 插件安装说明](https://docs.docker.com/compose/install/linux/)。已有可用 Docker Desktop 也可以继续使用。
2. 确认当前用户能够运行 `docker info` 和 `docker compose version`。安装后若服务未启动，按该发行版安装文档启动；若没有访问 Docker socket 的权限，按 [官方 Linux 安装后步骤](https://docs.docker.com/engine/install/linux-postinstall/) 配置后重新登录。项目脚本使用当前用户的 Docker，不在脚本内部自动 sudo。
3. 在终端执行：

```bash
git clone --branch common/phase0-bootstrap https://github.com/deep-hang/hadoop.git
cd hadoop
bash scripts/dev.sh doctor
```

4. 按下文 [获取镜像](#image) 导入镜像包或自行构建，然后在项目根目录执行：

```bash
bash scripts/dev.sh verify
bash scripts/dev.sh shell
```

Intel/AMD 的 x86_64 Linux 对应当前 `linux/amd64` 镜像。ARM Linux 的 Docker Engine 不一定已经配置非本机架构模拟；需按 [Docker 官方模拟说明](https://docs.docker.com/build/building/multi-platform/) 准备后再运行同样的验收，不自行改公共镜像的架构或版本。

镜像中的开发用户 UID 为 1000。若容器里写仓库出现 `Permission denied`，先退出容器，在宿主机用 `id -u`、`ls -ld .` 检查当前用户及仓库权限，按本机账户情况为开发用户授予工作目录写权限；不要直接把整个仓库设成所有人可写。

<a id="image"></a>
## 获取镜像：所有系统二选一

### A. 导入组长提供的镜像包

从组长分享的位置获取 `hadoop-base-v0.1.tar.gz`。在压缩包所在目录的终端执行：

```text
docker load --input hadoop-base-v0.1.tar.gz
```

预期提示 `Loaded image: hadoop-base:v0.1`。不需要手动解压；也可用引号括起压缩包的完整路径作为 `--input` 参数。导入后回到项目根目录执行对应系统的 verify，无需再执行 build。

镜像包与源码分别获取：镜像包不在 Git 仓库内，也不包含组员自己的代码。暂时没有镜像包时可以直接使用下面的构建方式，无需等待。

### B. 在自己电脑上构建

在项目根目录，Windows PowerShell 执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 build
```

macOS/Linux 终端执行：

```bash
bash scripts/dev.sh build
```

首次构建会下载镜像和 Hadoop，网络较慢时需要等待。构建成功后执行对应的 verify。下载问题可参考 [基础镜像与缓存说明](../docker/README.md)。

## 所有系统相同的验收结果

verify 最后应输出：

```text
BASE_API_PASS
PASS: frozen Java/Hadoop versions, paths, compiler and Hadoop API loading
```

通过后按 [成员接入与联调说明](member-onboarding.md) 建立自己的功能分支。无需提前报告操作系统；只有遇到错误时，反馈所执行的命令、完整报错和电脑系统/芯片信息，便于定位。

## 按报错自查

| 报错或现象 | 处理方法 |
| --- | --- |
| 找不到 git / docker | 先安装相应软件，关闭并重新打开终端，再检查版本 |
| 无法连接 Docker daemon / pipe / socket | Windows/Mac 先启动 Docker Desktop；Linux 检查服务与用户权限 |
| 找不到 hadoop-base:v0.1，或拉取它时提示 denied | 本项目尚未发布镜像到镜像仓库；先导入分享包或执行 build，再 verify |
| 找不到 scripts/dev.sh 或 .development | 切换到克隆下来的 hadoop 项目根目录，再执行命令 |
| Mac 提示目录挂载被拒绝 | 按 Docker Desktop 提示允许访问项目所在目录，必要时在文件共享设置中允许该目录 |
| `$'\r'`、`bad interpreter` | 使用 Git 克隆获取源码，编辑器换行设置为 LF；项目已有 .gitattributes 约定 |
| M 系列 Mac 运行较慢 | 保持公共 amd64 平台设置，先等基础验收完成；后续集群单独验收 |

目前实际测试过的是组长的 Windows 11 / Intel 电脑及其 Linux 容器；Mac 和其他 Linux 宿主机按以上官方安装流程与统一入口自行验收，未标记为已经实机测试。
