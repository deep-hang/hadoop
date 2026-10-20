# 公共接口 v0.1

`.development` 使用 UTF-8、LF、`KEY=value` 格式，兼容 Bash `source` 和 Compose `--env-file`。它记录公共契约，不存密码。修改版本、路径、节点名和应用入口需走公共变更流程。

## 节点和端点（供后续模块实现）

| 节点 | 服务 | 负责人 |
| --- | --- | --- |
| master | NameNode、ResourceManager | 2 号编排，3/4 号服务 |
| worker1 | DataNode、NodeManager | 2 号编排，3/4 号服务 |
| worker2 | DataNode、NodeManager | 2 号编排，3/4 号服务 |

HDFS URI 固定 `hdfs://master:9000`；NameNode Web UI 固定端口 `9870`；YARN Web UI 固定端口 `8088`。`master` 是容器网络内名称；宿主机后续通过 localhost 的端口映射看 Web 页面。这些端点在 Phase 0 尚未运行，环境变量 `HDFS_URI` 也不会自动启用 HDFS。

Hadoop 安装目录 `/opt/hadoop`，Java 目录 `/opt/java/openjdk`，配置目录 `/opt/hadoop/etc/hadoop`，工作目录 `/workspace`，日志目录 `/opt/hadoop/logs`。NameNode 数据目录约定 `/var/lib/hadoop/hdfs/namenode`，DataNode 数据目录约定 `/var/lib/hadoop/hdfs/datanode`。后续 2/3 号负责持久卷与目录权限；仅在未初始化的数据目录执行格式化。

## 应用接口（6、7 号实现）

公共脚本在 Linux 容器中用 Bash 运行，从任何当前目录调用都应可用：脚本应自行定位所在目录。

| 接口 | 参数 | 行为 / 退出码 |
| --- | --- | --- |
| `bash /workspace/apps/<app>/build.sh` | 无 | 编译本模块，产物保存在模块 `build/`，成功 0，失败非 0 |
| `bash /workspace/apps/<app>/run.sh <input> <output>` | 输入路径、输出路径 | 运行应用；具体模式和 URI 在模块 README 写明，成功 0，失败非 0 |
| `bash /workspace/apps/<app>/verify.sh <output>` | 输出路径 | 核对输出内容，正确 0，错误非 0 |

`<app>` 为 `wordcount` 或 `mergefile`。统一保留 `src/`、`input/`，测试数据可提交；编译产物不提交。HDFS 输入根目录 `/project/input`、输出根目录 `/project/output`，每个应用使用自己的子目录。输出已存在时应明确失败，不默认递归删除用户数据。若模块确有额外参数需要，先与组长协调并更新此契约。

上述脚本尚未实现，目录中的说明文件是交接位置。Phase 0 不提供返回成功的假脚本。

## 基础镜像入口

入口只检查 Java、Hadoop 和配置目录是否存在，然后 `exec` 指定命令，保留退出码及信号。默认进入 Bash。镜像用户为 `hadoop`（UID 1000），没有 sudo、SSH 服务或自动启动的集群。后续编排可以直接启动各守护进程；若确需 SSH，由对应模块提出依赖需求后统一变更基础镜像。

公共配置在构建时复制进镜像；修改 `config/common/` 后必须重新构建。仓库挂载至 `/workspace`，不会自动覆盖镜像中的 `/opt/hadoop/etc/hadoop`。
