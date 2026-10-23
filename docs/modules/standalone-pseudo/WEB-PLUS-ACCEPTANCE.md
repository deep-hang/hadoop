# 增强网页验收记录

验收日期：2026-10-23（Asia/Shanghai）。本轮仅新增文件，所有提交保留在本地 `feat/standalone-pseudo` 分支；未推送、未创建 PR。

## 源码与实测环境

| 项目 | 记录 |
| --- | --- |
| 开工基线 | `8188566`，工作区干净 |
| 最终功能代码 | `2476d716f4d732b0ab5ea3497cd0ffad08985ba9` |
| 网页命名调整 | `245d7d1`，浏览器标题及左上角名称改为 `Hadoop`，已实际刷新确认 |
| 完整原入口回归副本 | `runtime/member5/repro-web-plus/`，`cddc67f` |
| 最终增强入口复验副本 | `runtime/member5/repro-plus-final/`，`2476d71` |
| 运行环境 | Windows、Python 3.13.16、Docker Desktop Linux 引擎 |
| 统一镜像 | `hadoop-base:v0.1` |
| 镜像 ID | `sha256:6d9579105c8651df68fc3fbd5c3addea8706d610a8a005bd85ac734fb8551583` |
| Java / Hadoop | `1.8.0_442` / `3.3.6` |

`cddc67f` 后只补强新入口的 Unicode 诊断解析、损坏输出总数显示、预检查开始事件及归档证明的完整性判定，并增加对应测试；原入口、公共配置和基础镜像未变。两个复现副本都记录实际提交号及运行前后的 Git 干净状态。

## 自动检查

状态：下列检查全部通过。两个干净源码副本顺序执行 Docker 回归，未并行运行资源对照测试。

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| 最终增强入口单元测试 | 24 项通过 | 最终副本 `runtime/member5/web-plus-validation/unit-plus.log` |
| 最终增强前端逻辑 | 通过 | 同目录 `ui-plus.log` |
| 原网页单元 / 前端逻辑 | 15 项通过 / 通过 | `unit-original-web.log`、`ui-original-web.log` |
| 原增强终端入口单元测试 | 23 项通过 | `unit-console.log` |
| 公共契约 | 7 项通过 | `contract.log` |
| 增强网页真实集成 | `cddc67f` 与最终功能版本均为 16 项通过，单机清理各 1 项通过 | 两个副本各自的 `integration-plus.log` |
| 原网页真实集成 | 13 项通过，单机清理 1 项通过 | 完整副本 `integration-original-web.log` |
| 原单机 / 伪分布式回归 | 18 / 20 项通过，包含重启及容器重建持久化 | 完整副本 `standalone.log`、`pseudo.log` |
| 原增强终端真实回归 | 15 项通过，单机清理 1 项通过 | 完整副本 `integration-console.log` |
| 公共基础环境 | 通过 | 完整副本 `public-base.log` |

每个副本的 `runtime/member5/web-plus-validation/unit.json` 或 `full.json` 保存提交号、源码干净状态、步骤退出码和耗时。Docker 结果另见副本 `runtime/member5/tests/<项目名>/result.json`，包括项目归属、镜像、源码校验和清理结论。

新增真实集成覆盖：未就绪失败与输入恢复、显式初始化与启动、两种真实作业和存储挂载、共同输入与完整输出、文件修改时间与特殊文件名、64 KiB / 200 行预览、输出篡改与差异下载、重复行和损坏格式、缺少成功标记、空 TXT、离线报告、重跑关系、取消及异常进程恢复、HDFS 停止后的历史读取。最终复验额外使用 Java 不按空白拆分的 Unicode NEL 和 U+2028 词语。

## 浏览器与启动器

在本机内置 Chromium 实际完成：

1. 首页检查 Docker、镜像和 HDFS 状态；检查期间仍能编辑输入。
2. 上传 55 字节的 UTF-8 BOM 中文 TXT，切换伪分布式，首页显式启动已有 HDFS。文件名、预览和字节数保留，没有重新初始化。
3. 执行双模式对照 `cmp-20261023-043312-ba083b81`，两侧得到 6 个词、5 个不同词；`<script>` 内容只显示为文本。
4. 观察单机已完成、伪分布式继续执行的独立流程，展开真实 HDFS 目录、DataNode 数据块目录、副本数与专用卷。
5. 从结果进入 HDFS 输出，点击预览 `part-r-00000`；刷新后仍处于同一文件，内容与词频一致。
6. 仅修改本轮自行创建的单机演示输出，真实重新验证失败，页面显示“结果验证”失败阶段、原始错误及 5 项具体差异；随后恢复原字节并重新验证通过。失败证据仍保留。
7. 在默认窄视口和桌面宽度查看页面，确认两套流程可并排显示；已恢复原视口。浏览器未记录应用脚本错误。

浏览器真实作业在 `6c4ae98` 上执行；后续补强待采集证据措辞、Unicode 诊断、失败总数及归档证明判定，前端资源重新载入检查，功能代码另作独立自动复验。不把旧运行源码版本或采集时间改写为当前状态。

截图位于主工作区 `runtime/member5/web-plus-development/`：`compare.jpg`、`compare-desktop.jpg`、`diagnostic.jpg`、`storage.jpg`、`renamed-hadoop.jpg`。命名调整仅涉及本轮新增的增强网页资源，原网页资源保持原样。

PowerShell 从 `C:\Windows\system32` 实际启动新入口。PowerShell、Git Bash、CMD 在带空格的源码副本中从其他当前目录调用帮助成功；CMD 实际启动随机端口服务器并返回 HTTP 200，只终止本次创建的进程树。记录见主工作区 `runtime/member5/web-plus-development/wrappers.json`。

## 文件保护与资源归属

开工记录的 136 个已有文件均保持原 SHA-256。相对本轮 `8188566`，所有新增源码、测试和文档均处于成员 5 授权目录；相对团队 `edab708`，原文件差异仍仅限此前已获授权的五份 README。

基线、原文件审计、范围审计及最终汇总保存在主工作区 `runtime/member5/web-plus-development/`。运行输出、输入副本、截图及日志均位于被忽略的 `runtime/member5/`。

开发中失败的随机测试项目已经逐项检查标签并清理，记录在 `development-cleanup.json`。所有正式回归均完成归属检查与资源清理；最终增强项目为 `hadoop-m5-pseudo-test-0dcdf03ace` 和 `hadoop-m5-standalone-test-4320edc729`。公共基础验证容器运行后自动移除。

收尾时正常演示 HDFS 已停止，原数据卷保留；两个已有 `water-agent-quality-runtime` 容器继续运行。增强网页为用户核验保留在 `http://127.0.0.1:19875/`，当前浏览器页面已刷新为 `Hadoop`。没有停止 Docker 引擎，也未执行全局 Docker 清理。

最终功能复验为 `2476d71`；之后 `245d7d1` 只调整新增页面的两个名称位置，已通过实际浏览器标题、品牌文本及截图复核。文档整理不会改变已验证的执行逻辑。

## 验证边界

- 原生 Mac/Linux 未实测；Git Bash 不代表原生平台验收。
- 浏览器在本机内置 Chromium 实测，未覆盖全部浏览器。
- 离线 ZIP 检查 HTML、JSON、TSV 及安全转义；本轮未在浏览器中打开解压后的 `file://` HTML 做视觉验收。
- Docker 无法连接等异常有模拟单元测试，没有为故障注入而停止其他项目使用的 Docker 引擎。
- 没有进行大规模性能、多用户或局域网部署测试；入口仅供本机使用，耗时操作继续互斥。
- 本轮未加入浏览器草稿持久化、通用查询性能优化或持久化演示入口。

使用方法见 [WEB-PLUS.md](WEB-PLUS.md)。
