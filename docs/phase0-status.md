# Phase 0 验证报告

日期：2026-10-20（Asia/Shanghai）。状态：**公共底座本地构建、运行验收通过**；未推送远程，未修改 main。

后续环境准备：已通过 Windows 管理员确认启用 Virtual Machine Platform，状态由 `Disabled` 变为 `EnablePending`，WSL 可选组件原已启用。系统报告需重启，尚未自动重启。

Docker Desktop **4.96.0（243774）** 已按当前用户模式成功安装，安装包签名有效且发布者为 Docker Inc，安装程序退出码 **0**，日志记录 `Installation succeeded`。用户随后完成重启，硬件查询确认 HypervisorPresent=True；启动 Desktop 后 Linux 引擎就绪，CLI **29.9.1**、Compose **v5.6.0** 可用，项目配置解析、镜像构建和容器验证全部通过。

## 本机与仓库

| 项目 | 结果 |
| --- | --- |
| Git | `2.53.0.windows.3`，可用 |
| Docker CLI / Desktop | 29.9.1 / 4.96.0，已安装且可用 |
| Docker Compose | v5.6.0，随 Desktop 安装；初次静态校验也使用过临时独立 v2.40.3 |
| Docker 引擎 | Linux 引擎就绪，已完成构建和容器验证 |
| CPU 虚拟化 | Windows 硬件查询返回已启用 |
| WSL / 虚拟机平台 | 组件已准备，重启生效，HypervisorPresent=True |
| 远程仓库 | `https://github.com/deep-hang/hadoop`，克隆时为空 |
| 工作分支 | `common/phase0-bootstrap`，独立初始分支 |
| 提交 / 发布 | 以独立分支增量提交保存，未推送、未创建 main 或稳定标签 |

## 验证结果

| 验证项 | 结果 / 边界 |
| --- | --- |
| 基础镜像版本 | 已查询 Docker Registry，锁定的 JDK tag 存在，记录其 manifest SHA256 |
| Hadoop 校验值 | 与 Apache Archive 的 3.3.6 官方 SHA512 文件核对一致 |
| 公共契约检查 | `python tests/check-contract.py`：7 项通过 |
| Bash 语法 | 公共入口、开发入口、基础验证及入口行为验证脚本通过 |
| PowerShell 语法 | 使用 PowerShell 解析器检查通过 |
| 公共入口行为 | 缺少工具、缺少配置、子进程退出码、带空格参数传递，4 项在 Git Bash 和真实 Linux 容器中通过 |
| Compose 配置 | 随 Desktop 安装的 Compose v5.6.0 解析通过；构建上下文、工作区挂载及单服务范围也已核对 |
| 补丁空白检查 | `git diff --check` 通过（文件已标记 intent-to-add 供 diff 审阅） |
| Docker 构建 | 通过，官方安装包 SHA512 校验通过，生成 `hadoop-base:v0.1` |
| 容器内真实 JDK / Hadoop API 探针 | 通过：Java / javac 1.8.0_442、Hadoop 3.3.6；编译并运行 Hadoop Configuration 探针，输出 BASE_API_PASS |
| 开发入口 | PowerShell 的 doctor、build、verify 通过；Bash 的 verify 也通过 |
| HDFS / YARN / 模式 / 应用 | 不属于本次实现范围；均尚未实现 |

本次真实构建及 `verify` 已通过，达到公共底座运行验收门槛。首次直接下载因速度持续约 600 KB/s 主动停止，随后从同一官方地址分段下载完整安装包，校验通过后使用 `docker/cache/` 缓存成功构建。默认无缓存时仍可从官方地址构建。

本机验证镜像 ID：`sha256:6e4bccbd7b8bc109fa262f3ad9714df75c96226dd87c6b3fa183fa544a873b99`，平台 `linux/amd64`，运行用户 `hadoop`。该 ID 用于识别本次本地镜像；尚无远程镜像仓库 digest。

运行结果关键输出：

```text
openjdk version "1.8.0_442"
javac 1.8.0_442
Hadoop 3.3.6
BASE_API_PASS
PASS: frozen Java/Hadoop versions, paths, compiler and Hadoop API loading
```

## 下一步

1. 组长审阅独立分支中的公共契约及验证结果，再确定首次远程发布和 `v0.1-bootstrap` 标签；当前远程仓库仍无分支，不擅自创建 main。
2. 向成员交接相同源码版本与基础镜像。可分别构建，或由组长导出同一份已验证镜像供成员导入；不能只传本机路径。
3. 后续修改公共环境后重新运行 doctor、build、verify，并更新变更说明；当前 `.development` 已标为 `runtime-verified`。
4. 固定镜像后交接：2 号做三节点骨架，3/4 号分别接入 HDFS/YARN，5 号开展两种模式，6/7 号可先做应用自身代码及测试数据。
5. 向老师确认 Docker 替代 Linux 虚拟机、7 人汇报与视频时长的验收安排，见 `requirements.md`。

## 版本来源

- [Apache Java 兼容矩阵](https://cwiki.apache.org/confluence/spaces/HADOOP/pages/100827883/Hadoop+Java+Versions)
- [Apache Hadoop 3.3.6 官方 SHA512](https://archive.apache.org/dist/hadoop/common/hadoop-3.3.6/hadoop-3.3.6.tar.gz.sha512)
- [Docker Windows 安装要求](https://docs.docker.com/desktop/setup/install/windows-install/)
