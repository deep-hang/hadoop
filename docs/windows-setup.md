# Windows：WSL2 前置条件

仅在 Docker 安装提示缺少 WSL/虚拟化组件时使用。Docker 已可运行 Linux 容器的人跳过本文。

1. 按 [Docker 官方安装要求](https://docs.docker.com/desktop/setup/install/windows-install/) 核对系统；任务管理器 →“性能 → CPU”可查看本机虚拟化状态。
2. 在开始菜单搜索 PowerShell，右键“以管理员身份运行”。尚未安装 WSL 时，按官方流程执行：

```powershell
wsl --install --no-distribution
```

3. 按实际提示完成组件安装或更新；要求重启时保存文件并重启。
4. 打开 Docker Desktop，使用 WSL2 后端及 Linux 容器，等待引擎就绪。
5. 回到 [使用说明第 3 步](platform-setup.md#windows)，在普通 PowerShell 检查 Docker，再继续项目操作。

仍失败时保留完整错误发给组长，不反复卸载组件。无需额外安装 Ubuntu 发行版或本机 Java/Hadoop。
