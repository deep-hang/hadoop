# 补齐 5 号测试与运行指南入口

- 原因：main 的 `manage test` 调用了未交付的 Python 文件；模块入口仍写着未实现，运行指南还指向旧 fork 分支。
- 修改：从 5 号原 PR #1（d905aed）恢复单机、伪分布式核心测试及共用工具；按当前代码实测；将 Docker 内置网络的隔离核对改为按固定名称，应用网络/数据卷仍核对实际身份；更新两种模式和测试目录入口，运行指南改用团队 main。
- 影响：测试与文档；不修改 5 号运行代码和 2—4 号集群配置。测试使用随机项目，结束只清理该项目的容器、网络和测试卷。
- 验证：Windows PowerShell 两种 `manage.ps1 test` 均返回 0，单机 18 项、伪分布式 20 项通过；真实 Hadoop 作业、异常输入、错误输出识别、单节点 HDFS、重启/重建保留及资源隔离检查通过；公共契约 7 项通过。原生 Mac/Linux、网页全交互本次未复跑。
- 证据：本地 runtime/member5/tests/hadoop-m5-standalone-test-a32eb6240c/result.json、hadoop-m5-pseudo-test-5e5acdebab/result.json，不提交原始运行数据。
- 回滚：撤销本提交；已有演示容器及数据卷无需更改。若回滚，原 test 入口再次缺失，日常运行仍可使用。
