# 测试目录与执行方式

每人只在自己的子目录补充测试，不把模块脚本散放在 tests/ 根目录。

| 目录 | 负责人 | 验证内容 |
| --- | --- | --- |
| [common/](common/) | 1 号 | 公共契约、基础工具链和入口行为 |
| [distributed/](distributed/) | 2 号 | 三节点启动、网络连通与持久卷 |
| [hdfs/](hdfs/) | 3 号 | HDFS 读写、副本与双 DataNode |
| [yarn-mapreduce/](yarn-mapreduce/) | 4 号 | 资源管理、作业提交与双 NodeManager |
| [standalone/](standalone/) | 5 号 | 单机模式的输入、执行与输出 |
| [pseudo/](pseudo/) | 5 号 | 伪分布式服务、持久化与运行结果 |
| [wordcount/](wordcount/) | 6 号 | WordCount 固定输入与预期结果 |
| [mergefile/](mergefile/) | 7 号 | 多文件输入、合并语义与结果 |
| [integration/](integration/) | 1 号组织 | 各模块接入后的完整实验链路 |

## 组员怎么用

1. 按 [使用说明](../docs/platform-setup.md) 运行 verify，通过公共环境验收。
2. 本模块测试放上表对应目录，脚本使用具体名称，例如 check-upload.sh；在该目录 README.md 写清执行位置、命令、固定输入和预期结果。
3. 失败返回非零退出码；日志、临时输出不提交。WordCount/MergeFile 可复用 apps/ 对应目录的 input/，不重复复制测试数据。
4. 应用本身仍需保留 apps/ 内的 build.sh、run.sh、verify.sh 接口；tests/ 放额外用例，不替代这些接口。

除 common/ 现有脚本外，其他目录目前仅有交接说明，不代表测试已实现。

## 维护者检查公共底座

在项目根目录执行（Windows 的 Bash 命令使用 Git Bash）：

```text
python tests/common/check-contract.py
bash -n docker/entrypoint.sh
bash -n scripts/dev.sh
bash -n tests/common/verify-base.sh
bash -n tests/common/verify-entrypoint.sh
bash tests/common/verify-entrypoint.sh
```

公共运行环境变更后还需按 [镜像维护说明](../docker/README.md) 构建并运行 verify。仅移动挂载仓库内的测试文件无需重建镜像，但须复验入口调用。
