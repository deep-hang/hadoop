# 2 号：完全分布式编排

## 1. 你要完成什么

让一台电脑通过 Docker 启动 master、worker1、worker2 三个节点，接入 3 号的 HDFS 和 4 号的 YARN。最终别人按你的命令就能启动、进入、检查、停止集群。

先完成容器与网络骨架，尽早交给 3、4 号；不要等 PPT 做完再联调。

## 2. 在哪里改

| 位置 | 需要做什么 |
| --- | --- |
| compose/distributed.yaml（新建） | 正式三节点编排、网络、配置挂载、端口和独立数据卷 |
| compose/README.md | 补上正式启动、进入、日志、重启、停止命令 |
| tests/distributed/ | 添加节点解析、服务就绪和重启测试 |
| 本目录 | 记录实测结果、截图、PPT 和视频链接 |

不修改 compose/bootstrap.yaml。config/hdfs/ 由 3 号维护，config/yarn/ 由 4 号维护；通过 PR 同步他们的文件，不在自己的分支另写一套同名配置。

## 3. 按什么顺序做

1. 完成 [公共环境八步](../../platform-setup.md)，在 feat/distributed 分支开发。阅读 [公共启动说明](../../cluster-startup.md)。
2. 参考 [已验证的 Compose](../../../tests/common/fixtures/cluster/compose.yaml) 新建 compose/distributed.yaml。注意正式文件位于 compose/，相对挂载路径需重算：仓库根目录是 ..，不是测试文件中的 ../../../..。
3. 固定服务名与 hostname 为 master、worker1、worker2，使用 hadoop-base:v0.1、linux/amd64、init: true、同一网络。骨架阶段可以暂用保持运行的命令测试网络，但必须标注“仅骨架”，交付前换成真实服务入口。
4. 把仓库挂到 /workspace，master 需能读写应用目录，以便编译生成 build/ 产物。三个节点各有独立命名卷，挂到 /var/lib/hadoop；确认 UID 1000 可写，不能共用同一个数据卷。
5. 等 3、4 号的配置合入 main 后，在自己的功能分支同步 origin/main。逐文件挂载四个 site XML 到 /opt/hadoop/etc/hadoop，不覆盖整个配置目录。环境变量及 JVM 资源参考测试 Compose，再根据电脑实测调整。
6. 节点命令分别调用 bash /workspace/scripts/hadoop-node.sh master 或 worker。首次显式执行 init-namenode；普通启动和重启不格式化。不使用依赖 SSH 的 start-dfs.sh / start-yarn.sh。
7. master 映射 127.0.0.1:9870:9870、127.0.0.1:8088:8088。记录 Docker CPU/内存、启动等待和失败时查日志的方法。
8. 按下方顺序实测，再交给 6、7 号进入 master 提交应用。

## 4. 正式文件完成后怎样操作

下面命令在电脑终端、项目根目录执行，Windows/Mac 相同。**目前 distributed.yaml 尚未实现，先完成以上开发再运行。**

~~~text
docker compose --env-file .development -p hadoop-distributed -f compose/distributed.yaml config --quiet
docker compose --env-file .development -p hadoop-distributed -f compose/distributed.yaml run --rm --no-deps master bash /workspace/scripts/hadoop-node.sh init-namenode
docker compose --env-file .development -p hadoop-distributed -f compose/distributed.yaml up -d
docker compose --env-file .development -p hadoop-distributed -f compose/distributed.yaml ps
docker compose --env-file .development -p hadoop-distributed -f compose/distributed.yaml exec master bash
~~~

最后一条进入 master，以下在容器内逐条执行：

~~~bash
getent hosts worker1 worker2
hdfs dfsadmin -report
yarn node -list
~~~

两个 worker 也需能解析 master。Live datanodes 应为 2，YARN RUNNING 节点应为 2；只看到容器 Up 不算通过。

在容器输入 exit 后回电脑终端，查日志、重启或停止：

~~~text
docker compose --env-file .development -p hadoop-distributed -f compose/distributed.yaml logs --tail 100
docker compose --env-file .development -p hadoop-distributed -f compose/distributed.yaml restart
docker compose --env-file .development -p hadoop-distributed -f compose/distributed.yaml down
~~~

普通停止不加 --volumes，不删除持久数据。遇到启动失败先看对应服务日志，不靠重新格式化解决。

## 5. 怎样算完成

- 三节点互相解析；两个 DataNode、两个 NodeManager 注册。
- 配合 3、4 号完成 HDFS 读写和真实 YARN 作业。
- 重启后服务恢复、原文件仍可读；停止能清理进程。
- tests/distributed/ 写明检查命令，失败返回非零；记录实测 CPU/内存和等待时间。
- 本目录补配置说明、拓扑图、启动与重启证据、PPT 和含字幕配音的视频链接。
- 按 [协作规则](../../contributing.md) 提 PR 到 main。演示讲清容器、网络、挂载、数据卷与三种部署模式的区别。
