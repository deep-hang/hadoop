# Windows 容器前置条件

首次检查：Git 可用；未发现 Docker Desktop，`docker` 不在 PATH；CPU 报告 BIOS 虚拟化已开启；WSL 状态提示 WSL2 所需组件尚未准备好。

2026-10-20 后续准备：已通过 Windows 管理员确认运行 `scripts/windows-enable-wsl.ps1`。虚拟机平台由 `Disabled` 变为 `EnablePending`，WSL 组件原本为 `Enabled`，系统明确要求重启。没有自动重启，也没有修改 BIOS；没有发现需要更改的 hypervisor 启动项。

Docker Desktop 4.96.0 已按当前用户模式成功安装，安装包的 Docker Inc 发布者签名验证通过，安装程序退出码 0。安装位置为 `%LOCALAPPDATA%\Programs\DockerDesktop`，Docker CLI 29.9.1、Compose v5.6.0 均可用。用户已经重启，虚拟机平台已生效，Docker Linux 引擎启动成功，公共镜像构建及运行验证通过；本机无需重复下载安装或启用组件。以下步骤供其他尚未配置环境的成员参考。

## 完成环境安装

1. 按 [Docker 官方 Windows 安装说明](https://docs.docker.com/desktop/setup/install/windows-install/) 检查系统要求。
2. 在管理员 PowerShell 中按官方流程启用 WSL 与 Virtual Machine Platform（可使用 `wsl --install --no-distribution`），根据系统提示重新启动。此操作不是在项目普通终端中执行。
3. 安装 Docker Desktop，选择 WSL2 后端及 Linux 容器，启动后等待引擎就绪。完成首次运行协议等交互。
4. 重新打开终端，在仓库根目录运行 `scripts/dev.ps1 doctor`、`build`、`verify`（完整调用见 README）。

若仍提示虚拟化不可用，结合 Windows 可选组件和 WSL 的实际错误排查；硬件查询已报告 BIOS 开启，不应仅凭 WSL 通用提示去改 BIOS。

公共脚本 `scripts/windows-enable-wsl.ps1` 可在管理员 PowerShell 中重新执行，保留组件前后状态并报告是否需要重启，默认将结果写入当前用户临时目录的 `hadoop-windows-components.json`。脚本不自动重启。完成 Docker 安装后无需安装本机 Java/Hadoop。

## 常见问题

- 找不到 docker：安装未完成或终端尚未刷新 PATH。
- 无法连接引擎：启动 Docker Desktop，并确认 Linux 容器后端正常。
- 拉取镜像失败：检查 Docker Desktop 的代理和网络配置；不要随意替换项目版本。
- Linux 宿主机挂载目录不可写：镜像使用 UID 1000；在宿主机为工作目录设置适当的用户权限，或先协调用户映射。
