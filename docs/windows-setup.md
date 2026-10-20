# Windows：Docker 安装前置条件（新成员按顺序操作）

本文只处理 Windows 安装 Docker 时的前置问题。完整项目步骤见 [Windows 第 1—8 步](platform-setup.md#windows)。如果那里的第 3 步已全部通过，不需要重新启用组件、安装软件或重启。

## 第 1 步：核对本机是否符合要求

1. 打开 [Docker 官方 Windows 安装说明](https://docs.docker.com/desktop/setup/install/windows-install/)，核对自己的 Windows 版本、WSL 和硬件要求。
2. 在任务管理器的“性能 → CPU”查看“虚拟化”状态。组长电脑已开启不代表所有组员电脑都已开启；按自己电脑状态处理。
3. 如硬件或系统不符合要求，先按官方说明解决，不继续执行项目构建。

## 第 2 步：打开管理员 PowerShell，准备 WSL2 组件

1. 在开始菜单搜索 PowerShell，右键选择“以管理员身份运行”，确认系统授权提示。
2. 按 Docker 官方 WSL2 安装流程准备组件。尚未安装 WSL 时，可在管理员窗口执行：

```powershell
wsl --install --no-distribution
```

3. 如果系统报告已有安装或其他错误，按实际提示和官方安装说明处理，不反复卸载组件。项目不要求为了 Docker 单独安装 Ubuntu 发行版。
4. 如果提示要重新启动，保存文件后重启电脑，再继续。关闭终端不能替代重启。

仓库里的 scripts/windows-enable-wsl.ps1 是组长诊断时使用的可选辅助脚本，不是成员必须重复运行的步骤。它只启用相关组件并报告状态，不自动重启。

## 第 3 步：安装并打开 Docker Desktop

1. 从 Docker 官方 Windows 安装页获取适合本机的安装包，按页面流程安装。
2. 使用 WSL2 后端与 Linux 容器，完成安装及首次运行提示。
3. 从开始菜单打开 Docker Desktop，等待引擎运行成功；如果提示 WSL 需要更新，按官方流程处理后重试。
4. 如果提示虚拟化不可用，结合自己电脑的虚拟化状态、Windows 组件和具体错误排查，不直接照搬组长机器的历史判断。

## 第 4 步：用普通 PowerShell 验证

关闭安装前打开的旧终端，重新打开普通 PowerShell，逐条执行：

```powershell
docker --version
docker compose version
docker info --format '{{.OSType}}'
```

前两条应显示版本，第三条应显示 linux。任意一条失败都先处理，不继续构建。后续项目命令不要求管理员权限。

## 第 5 步：失败时按顺序自查

1. 找不到 docker：确认安装已完成，关闭并重开终端，再检查。
2. 无法连接引擎：打开 Docker Desktop，等待启动完成，核对 Linux 容器模式。
3. 引擎因 WSL 或虚拟化启动失败：保留完整错误，按官方安装说明检查缺少的组件、更新或重启要求。
4. 仍无法解决：将完整报错、已完成的步骤和电脑系统信息发给组长。

## 第 6 步：回到项目说明继续

回到 [Windows 使用顺序](platform-setup.md#windows)，从第 4 步下载代码开始；已经下载过的成员按“已有项目怎么办”核对，再继续配置检查、镜像获取和验证。无需在 Windows 本机另装 Java/Hadoop。

组长机器的实际安装和验证结果见 [Phase 0 验证报告](phase0-status.md)，它是历史记录，不代表其他成员已经完成安装。
