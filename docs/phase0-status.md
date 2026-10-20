# Phase 0 验证记录

日期：2026-10-20（Asia/Shanghai）。公共底座已通过本地验收，发布于 common/phase0-bootstrap；未创建 main 或 v0.1-bootstrap 稳定标签。

## 实测环境

Windows 11 / Intel；Git 2.53.0；Docker Desktop 4.96.0、CLI 29.9.1、Compose 5.6.0。WSL2 与虚拟机平台已配置，重启后 Linux 容器可运行。

## 已通过的验证

| 项目 | 结果 |
| --- | --- |
| 版本和下载校验 | 固定 JDK digest，Hadoop 官方 SHA512 一致 |
| 静态检查 | 7 项公共契约检查及 Bash / PowerShell 语法检查通过 |
| 入口行为 | 缺少工具/配置、退出码、带空格参数，在 Git Bash 和 Linux 容器验证通过 |
| 构建与运行 | doctor、build、verify 通过；Java/javac 1.8.0_442、Hadoop 3.3.6、Hadoop API 探针通过 |
| 干净源码 | 新克隆到含中文和空格的目录，使用已有镜像通过 doctor / verify |
| 镜像分发 | 导出、重新导入后镜像 ID 一致；上传大小及 SHA256 一致，无需登录的下载请求成功 |

Mac 尚未实机验收。三节点、HDFS/YARN、运行模式和两个应用属于后续模块。

## 已分发镜像

[GitHub 发布页](https://github.com/deep-hang/hadoop/releases/tag/phase0-image-v0.1) · [下载镜像包](https://github.com/deep-hang/hadoop/releases/download/phase0-image-v0.1/hadoop-base-v0.1.tar.gz)

- 镜像：hadoop-base:v0.1，linux/amd64，用户 hadoop（UID 1000）。
- 镜像 ID：sha256:6d9579105c8651df68fc3fbd5c3addea8706d610a8a005bd85ac734fb8551583。
- 压缩包大小：828,594,929 字节。
- 压缩包 SHA256：0a1f1e6b5148c2d74811fab39b4667c4ead199930052ac28dd99a40eb3700453。

## 后续工作

1. 成员按 [使用说明](platform-setup.md) 完成本机验收并开发。
2. 组长按 [联调要求](member-onboarding.md) 集成，确认 [课程验收差异](requirements.md)。
3. 公共环境有改动时重新构建验证，再更新镜像分发和记录。

版本依据：[Apache Java 兼容说明](https://cwiki.apache.org/confluence/spaces/HADOOP/pages/100827883/Hadoop+Java+Versions)、[Hadoop 3.3.6 官方 SHA512](https://archive.apache.org/dist/hadoop/common/hadoop-3.3.6/hadoop-3.3.6.tar.gz.sha512)。
