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

## 联调时统一怎么用

1. 当前方案是在一台电脑上运行 master、worker1、worker2 三个独立容器，每人可在自己电脑复现；不是把组员的电脑分别当作三个节点。老师已接受 Docker，确认记录见 [验收要求](requirements.md)。
2. 完全分布式阶段统一从 master 容器提交应用。2 号交付进入该容器的完整命令，并挂载 /workspace；3、4 号让它和 Worker 使用同一套有效配置。
3. config/hdfs/ 由 3 号提供 core-site.xml、hdfs-site.xml；config/yarn/ 由 4 号提供 yarn-site.xml、mapred-site.xml。2 号逐文件接入实际 Hadoop 配置目录，不让一套配置覆盖另一套；配置加载后再验收。
4. 最终 run.sh / verify.sh 的路径按 HDFS 解释，例如 /project/input/wordcount、/project/output/wordcount/run-001。测试输入先由仓库 input/ 上传 HDFS；重复演示使用新的输出子目录，不默认删除旧结果。
5. 基础镜像包含 javac、jar，没有 Maven、SSH 客户端或 SSH 服务。应用优先用现有工具编译；若确需其他依赖，先由组长统一处理，不能只在某个人容器里手工安装。
6. 2、3、4 号复用 [公共启动脚本](cluster-startup.md)，在各容器本地启动并管理服务。不要直接照搬依赖 SSH 的 start-dfs.sh / start-yarn.sh。

启动方式依据 [Hadoop 3.3.6 官方集群说明](https://hadoop.apache.org/docs/r3.3.6/hadoop-project-dist/hadoop-common/ClusterSetup.html)。公共启动能力提供独立三节点复验；正式集群仍由 2—4 号交付，见 [启动说明](cluster-startup.md)。
