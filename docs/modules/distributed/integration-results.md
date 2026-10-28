\# 二号任务：三节点集群联合验证



\## 验证环境与代码



\- 验证日期：2026-10-28

\- 操作系统：Windows，Docker 使用 Linux 容器

\- 镜像：hadoop-base:v0.1

\- Docker 可用资源：12 CPU，8209084416 字节内存

\- 联调分支：integration/distributed-pr5-pr6

\- 联调基础提交：a678d64

\- 配套 HDFS PR：#5，提交 50ed80c

\- 配套 YARN PR：#6，提交 5154bd7

\- 在上述代码上修改 compose/distributed.yaml 后进行测试

\- 实测 Compose 项目名：hadoop-distributed-recovery



\## 编排实现



\- master：NameNode、ResourceManager。

\- worker1、worker2：分别运行 DataNode、NodeManager。

\- 三个节点使用同一网络、固定服务名和 hostname。

\- 仓库读写挂载至 /workspace。

\- 四份 HDFS/YARN XML 逐文件只读挂载。

\- 每个节点有独立命名卷，挂载至 /var/lib/hadoop。

\- master 将 9870、8088 端口映射到宿主机 127.0.0.1。

\- 使用公共 hadoop-node.sh 启动服务，不依赖 SSH。

\- 首次显式初始化 NameNode，普通启动和重启不格式化。



\## 实测结果



1\. 两个 DataNode 注册成功，两个 NodeManager 为 RUNNING。

2\. HDFS 配置、读写和块副本检查通过，HDFS\_TEST\_PASS，退出码 0。

3\. 执行 persistence record 后，通过不带 --volumes 的 down 和 up -d 重建容器。

4\. 重建后安全模式为 OFF，两个 NodeManager 恢复 RUNNING。

5\. persistence verify 输出 HDFS\_PERSISTENCE\_PASS，退出码 0。

6\. 重建前后测试文件 SHA256 与块 ID 完全一致。

7\. YARN 作业 application\_1793151638813\_0001 为 FINISHED / SUCCEEDED。

8\. 输出 hadoop=8000、hello=8000，与预期一致。

9\. worker1、worker2 各成功完成 4 个 Map 和 1 个 Reduce。

10\. YARN 检查退出码为 0。



YARN 检查命令：



python tests/yarn-mapreduce/check-yarn.py --project hadoop-distributed-recovery



本机证据目录：



runtime/yarn-check-20261028-094334/



该目录不提交 Git，交接时保留原始证据。



\## 故障与验证边界



旧项目 hadoop-distributed 曾发生三个容器同时退出，退出码 255。

随后发现 13 个块被标记损坏，抽查的一个块在两个 Worker 上的数据

及校验文件均为零字节。具体根因尚未确定。



旧数据卷保留。本次使用 hadoop-distributed-recovery 创建独立新卷，

重新生成测试数据并完成验证，不代表旧损坏数据已经恢复。



HDFS 块检查脚本对部分统计字段误报“未包含”，需要反馈给 3 号修正；

本次原始 fsck 输出显示所检查文件 HEALTHY，损坏块为 0，双副本有效。



启动等待时间尚未精确测量。正常停止、重建测试通过，

不代表已经验证突然断电或 Docker/WSL 崩溃后的数据可靠性。
