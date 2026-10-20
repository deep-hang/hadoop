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

<a id="submit"></a>
## 测试成功后，怎样交给组长

以下 Git 命令在**电脑终端、项目根目录**执行；还在容器里时先输入 exit。提交 PR 就是申请合并，不会立即改动 main。

1. 执行下面两条，确认当前分支显示 feat/distributed，并检查本次修改。显示 main 时先切回自己的分支；不要在 main 提交模块代码。

~~~text
git branch --show-current
git status
~~~

2. 把本模块文件加入提交，查看文件清单，再保存、推送。下面路径须已完成创建；如某文件尚不存在，先从命令中去掉该项。提交说明改成自己本次实际完成的内容。

~~~text
git add compose/distributed.yaml compose/README.md tests/distributed/ docs/modules/distributed/
git diff --cached --stat
git commit -m "feat(distributed): complete module implementation and validation"
git push -u origin feat/distributed
~~~

核对没有误加他人的文件、日志或编译产物再 commit。首次提交若提示身份未配置，按提示设置本仓库的 git config user.name 和 git config user.email。推送报权限错误时，确认已接受组长的仓库邀请并登录自己的 GitHub 账号。

3. 打开 [仓库 PR 页面](https://github.com/deep-hang/hadoop/pulls)，点击 New pull request：**base 选 main，compare 选 feat/distributed**。
4. 检查 Files changed，点击 Create pull request。写清做了什么、运行命令、实际测试结果和未完成项；未测试通过的工作使用 Draft，暂不申请合并。
5. 等组长审核。收到修改意见后，仍在 feat/distributed 修改、复测，再重复第 2 步；原 PR 会自动更新，不用另建 PR。
6. 组长复验后批准并点击 Merge pull request，代码才进入 main。成员不直接推送 main，也不自行合并 PR。

**需要获取其他成员已合入的代码时**：先在自己的分支提交保存修改，确认 git status 干净，再执行：

~~~text
git fetch origin
git merge origin/main
~~~

有冲突时联系相关负责人解决，重新测试后 git push。此过程保留自己的功能分支；后续继续开发仍用 feat/distributed，不用重复 git switch -c。更多说明见 [协作规则](../../contributing.md)。
