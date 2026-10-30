\# 二号任务：三节点骨架阶段实验记录



\## 环境



\- 操作系统：Windows

\- Git：2.56.0.windows.3

\- Docker：29.9.2

\- Docker Compose：v5.6.1

\- 基础镜像：hadoop-base:v0.1

\- Java：1.8.0\_442

\- Hadoop：3.3.6

\- 开发分支：feat/distributed



\## 当前实现



compose/distributed.yaml 定义 master、worker1、worker2。

三个节点使用同一个 Docker 网络。

仓库挂载至 /workspace。

每个节点使用独立命名卷，挂载至 /var/lib/hadoop。



当前使用 sleep infinity 保持容器运行，仅为容器与网络骨架。

尚未启动 HDFS 和 YARN。



\## 已完成的手工验证



1\. 公共环境 verify 输出 BASE\_API\_PASS。

2\. 三个容器均为 Up。

3\. 每个节点均能解析另外两个节点的名称。

4\. 三个节点均以 UID 1000 运行，数据目录可写。

5\. 各节点将自己的主机名写入数据卷中的测试文件。

6\. 执行不带 --volumes 的 down，然后执行 up -d。

7\. 重建后读取测试文件，三个节点内容均与各自主机名一致。



结论：三节点骨架、数据目录权限和测试文件持久化验证通过。

该结果不代表 HDFS/YARN 服务或 HDFS 数据持久化验收通过。



\## 自动检查



命令：



powershell -NoProfile -ExecutionPolicy Bypass -File .\\tests\\distributed\\check-skeleton.ps1



自动检查结果：输出 SKELETON\_CHECK\_PASS，退出码为 0。

三个节点的主机名、相互名称解析、UID 1000 和数据目录写入权限全部通过。



\## 后续工作



\- 接入 3 号的 core-site.xml、hdfs-site.xml。

\- 接入 4 号的 yarn-site.xml、mapred-site.xml。

\- 使用公共 hadoop-node.sh 启动真实服务。

\- 配置 master 的本机 Web 端口映射。

\- 验证两个 DataNode 和两个 NodeManager 注册。

\- 验证 HDFS 读写、真实 YARN 作业及服务重启后数据保留。

\- 补充资源配置、启动等待时间、截图、PPT 和视频。
