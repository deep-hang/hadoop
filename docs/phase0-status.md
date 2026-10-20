# Phase 0 验证报告

日期：2026-10-20（Asia/Shanghai）。状态：**公共底座本地构建、运行验收通过**；已发布至 GitHub 的 `common/phase0-bootstrap` 分支，未创建或修改 main。

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
| 提交 / 发布 | 已增量提交并推送 `origin/common/phase0-bootstrap`，未创建 main 或稳定标签 |

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

首轮构建记录的镜像 ID：`sha256:6e4bccbd7b8bc109fa262f3ad9714df75c96226dd87c6b3fa183fa544a873b99`，平台 `linux/amd64`，运行用户 `hadoop`。该记录用于识别当时本地镜像；尚无远程镜像仓库 digest。

运行结果关键输出：

```text
openjdk version "1.8.0_442"
javac 1.8.0_442
Hadoop 3.3.6
BASE_API_PASS
PASS: frozen Java/Hadoop versions, paths, compiler and Hadoop API loading
```

## 成员接入复验

另从 GitHub 公共分支克隆了一份干净源码，目录名包含中文和空格，未复制原仓库的安装包缓存；使用本机已有的已验收镜像运行 doctor 和 verify，均通过。该结果证明干净源码可以复用镜像，不代表已在其他组员电脑上测试，也不替代新机器首次构建或导入镜像的验证。

新增 `member-onboarding.md`，明确按系统自行接入、共享镜像导入、各模块分支来源和逐层联调门槛。尤其明确基础 dev 容器不自动加入未来集群；应用的提交容器、网络和配置挂载须由 2、3、4 号交付并验收。

成员接入复验时本地镜像 ID 为 `sha256:6d9579105c8651df68fc3fbd5c3addea8706d610a8a005bd85ac734fb8551583`，工具版本与契约一致。已从该镜像导出独立交付文件 `hadoop-base-v0.1.tar.gz`（约 829 MB，不在 Git 仓库内），并用 Docker 实际重新导入成功，导入前后镜像 ID 一致，现通过 [GitHub Release](https://github.com/deep-hang/hadoop/releases/tag/phase0-image-v0.1) 提供成员下载（镜像分发预发布）。每位成员仍须在自己的机器上导入镜像并运行验证。

GitHub 附件上传验证：文件大小 828,594,929 字节；上传数据与 GitHub 服务端 SHA256 一致（0a1f1e6b5148c2d74811fab39b4667c4ead199930052ac28dd99a40eb3700453）。无需登录的下载请求返回 HTTP 206，文件头为 gzip。该校验对象是压缩镜像包，与 Docker 镜像 ID 不同。

## 下一步

1. 组长审阅已发布分支中的公共契约及验证结果，再确定 main 与 `v0.1-bootstrap` 稳定标签；公共底座仍以工作分支开发；镜像分发预发布不替代正式稳定发布。
2. 向成员交接相同源码版本与基础镜像。可分别构建，或由组长导出同一份已验证镜像供成员导入；不能只传本机路径。
3. 后续修改公共环境后重新运行 doctor、build、verify，并更新变更说明；当前 `.development` 已标为 `runtime-verified`。
4. 固定镜像后交接：2 号做三节点骨架，3/4 号分别接入 HDFS/YARN，5 号开展两种模式，6/7 号可先做应用自身代码及测试数据。
5. 向老师确认 Docker 替代 Linux 虚拟机、7 人汇报与视频时长的验收安排，见 `requirements.md`。

## 版本来源

- [Apache Java 兼容矩阵](https://cwiki.apache.org/confluence/spaces/HADOOP/pages/100827883/Hadoop+Java+Versions)
- [Apache Hadoop 3.3.6 官方 SHA512](https://archive.apache.org/dist/hadoop/common/hadoop-3.3.6/hadoop-3.3.6.tar.gz.sha512)
- [Docker Windows 安装要求](https://docs.docker.com/desktop/setup/install/windows-install/)
