# Phase 0 初始公共底座（本地验证通过）

- 修改人：组长工作区，由 Codex 执行。
- 修改类型：空仓库首次初始化；公共接口新增。
- 涉及模块：docker、公共 config、bootstrap compose、scripts、tests、docs、`.development`；其余仅创建交接目录。
- 原因与必要性：为 2–7 号提供统一 JDK/Hadoop 版本、路径、节点命名与脚本接口，避免各自建立不兼容环境。
- 修改前：远程仓库为空，无稳定提交和运行行为。
- 修改后：提供已完成本地构建和运行验收的公共环境定义与自检入口。
- 接口变化：新增 `.development` 契约；应用接口是预留规范，尚无模块实现。
- 影响范围：全组后续开发；不包含现有模块迁移。
- 本地测试 / 回归：见 `docs/phase0-status.md`；空仓库无既有功能回归对象。
- 回滚版本：无历史稳定版本，不伪造 `v0.1-bootstrap`。
- 回滚方式：公共底座以独立分支增量提交保存，未修改 main；后续通过 revert 和 PR 回退具体公共变更，不删除或重写 main。

## 后续宿主机准备

新增 `scripts/windows-enable-wsl.ps1`，仅用于 Windows 宿主机组件准备，要求管理员权限；记录状态、不自动重启。实际执行已将 VirtualMachinePlatform 从 Disabled 置为 EnablePending，WSL 组件本来已启用。未更改公共镜像或应用接口。该宿主机动作不会随 Git 回退；如以后不再需要虚拟化功能，须评估其他 WSL/Docker 使用后再由管理员关闭组件。

Docker Desktop 4.96.0 已通过官方安装包按当前用户模式安装，验证了发布者签名，安装退出码 0。新安装的 Docker 29.9.1 和 Compose v5.6.0 可用，项目配置解析通过；引擎仍待系统重启及应用启动。文档将 Compose 要求表述为 v2 或以上，未改变运行接口。

重启后 Docker Linux 引擎已就绪。由于 Apache Archive 单路下载持续约 600 KB/s，增加可选的 `docker/cache/` 官方安装包缓存路径，构建时无论是否命中缓存都执行固定 SHA512 校验；缓存缺省时保持从官方地址下载。安装包已加入 Git 忽略列表，版本、运行配置及应用接口不变。

本地真实构建通过。PowerShell doctor/build/verify、Bash verify、Linux 容器内入口行为验证通过；Java/javac 1.8.0_442、Hadoop 3.3.6 均与契约一致，Hadoop API 编译运行探针输出 BASE_API_PASS。`.development` 状态更新为 runtime-verified；2–7 号模块未实现。镜像 ID 及完整结果记录在 `docs/phase0-status.md`。

## 分支发布

用户明确要求发布后，已推送 `common/phase0-bootstrap` 至 `origin` 并设置上游跟踪。同步更新 README、验收报告和协作说明中的发布状态；未创建或修改 main，未发布稳定标签，未上传大型安装包或本地镜像。

## 成员接入准备

针对组员复现与后续拼接的担心，新增成员接入及联调验收说明，补齐源码获取、镜像导入、分支来源和分阶段交接要求。实际验证了从 GitHub 重新克隆、含中文和空格的目录，在没有源码下载缓存的情况下使用现有镜像通过 doctor/verify。该复验仍在组长电脑进行，不宣称其他系统或未来模块已经验收。另准备可供组长分享的镜像导出包，镜像和安装包不进入 Git。

导出包已用 Docker 实际重新导入成功，导入前后镜像 ID 一致。说明文件经文档链接及公共契约检查通过，不修改运行环境或公共接口。
