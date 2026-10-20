# 公共配置（1 号维护）

hadoop-env.sh 固定 Java/Hadoop 路径与日志目录；core-site.xml 保持空配置，基础环境沿用 Hadoop 自带的本地默认值；workers 预留完全分布式节点名 worker1、worker2，不启动服务。此目录在镜像构建时复制，修改后需要重新构建。
