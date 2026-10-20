# 4 号：YARN / MapReduce 分布式计算

## 1. 你要完成什么

让 master 运行 ResourceManager，两个 worker 运行 NodeManager；用真正的 YARN 作业证明任务能完成，并记录两个 worker 的计算参与情况。

## 2. 在哪里改

- config/yarn/yarn-site.xml、mapred-site.xml（新建）：资源管理和 MapReduce 配置。
- tests/yarn-mapreduce/：节点注册、示例任务、结果和任务分布检查。
- config/yarn/README.md：配置含义、资源参数和运行方法；本目录放实验结果及 PPT/视频链接。
- 2 号接入编排；3 号提供 HDFS；不改他们的文件来维护第二套配置。

## 3. 按什么顺序做

1. 通过公共环境验证，在 feat/yarn-mapreduce 开发。阅读 [公共启动说明](../../cluster-startup.md)，参考 [已验证配置](../../../tests/common/fixtures/cluster/)。
2. yarn-site.xml 设置 ResourceManager 为 master、启用 mapreduce_shuffle；配置 NodeManager 内存/vcores 和调度器分配范围。
3. mapred-site.xml 设置 mapreduce.framework.name=yarn，并配置应用类路径、AM、Map、Reduce 内存和 JVM 堆。任务内存必须能装进节点资源；参考参数是最小验证样例，不是所有电脑的固定标准。
4. 把配置及所需 HADOOP_* 环境、JVM 参数交给 2 号挂载。等 HDFS 就绪后，确认两个 NodeManager 注册成功。
5. 先用 Hadoop 自带 WordCount JAR 打通作业链路；这是环境验证，不替代 6 号实现自己的 WordCount。
6. 多个输入文件产生多个输入分片，核对实际任务数和容器所在节点。只看到两个 NodeManager 在线，不代表两个 worker 都算过任务。
7. 保存 application ID、成功状态、结果、两个节点的任务证据，通知 6、7 号可开始真实集群联调。将检查整理到自己的 tests/ 目录。

若配置与 2 号编排互相等待，先提交配套 Draft PR，按 [联合验证流程](../../member-onboarding.md#joint-check) 共同测试，再审核合入。

## 4. 怎样验证

**前提：2 号正式集群已接入 3、4 号配置且服务就绪。** 按 [2 号说明](../distributed/README.md) 进入 master，以下均在 master 内执行：

~~~bash
yarn node -list
hdfs getconf -confKey fs.defaultFS
mkdir -p /tmp/yarn-demo
for n in 1 2 3 4 5 6 7 8; do printf 'hello hadoop\n' > /tmp/yarn-demo/part-$n.txt; done
hdfs dfs -mkdir -p /project/input/yarn-demo
hdfs dfs -put /tmp/yarn-demo/*.txt /project/input/yarn-demo
hadoop jar /opt/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar wordcount /project/input/yarn-demo /project/output/yarn-demo/run-001
hdfs dfs -cat '/project/output/yarn-demo/run-001/part-r-*'
yarn application -list -appStates ALL
~~~

预期两个 RUNNING 节点，任务有 application ID、最终成功，输出 hadoop=8、hello=8。重复演示换新输出目录；已有输入不用重复 put。

在电脑浏览器打开 http://localhost:8088 查看作业。两个 worker 的 /opt/hadoop/logs/userlogs 中可查对应 application 的任务日志；区分 ApplicationMaster 与 Map/Reduce 容器，记录实际运行任务的节点。若只用了一个 worker，检查分片数量、资源余量和调度，再调整演示输入。

## 5. 怎样算完成

两节点注册、真实 YARN 作业成功、正确输出、两个 worker 的计算证据均齐全；记录 Docker 资源、YARN 资源及任务内存的关系。

PPT/视频讲清 ResourceManager、NodeManager、ApplicationMaster、Map/Shuffle/Reduce，按“配置 → 注册 → 提交 → 状态 → 节点任务 → 结果”演示。补好本目录实测记录，按 [协作规则](../../contributing.md) 提 PR 到 main。

参考：[MapReduce 官方教程](https://hadoop.apache.org/docs/r3.3.6/hadoop-mapreduce-client/hadoop-mapreduce-client-core/MapReduceTutorial.html)。

<a id="submit"></a>
## 测试成功后，怎样交给组长

以下 Git 命令在**电脑终端、项目根目录**执行；还在容器里时先输入 exit。提交 PR 就是申请合并，不会立即改动 main。

1. 执行下面两条，确认当前分支显示 feat/yarn-mapreduce，并检查本次修改。显示 main 时先切回自己的分支；不要在 main 提交模块代码。

~~~text
git branch --show-current
git status
~~~

2. 把本模块文件加入提交，查看文件清单，再保存、推送。下面路径须已完成创建；如某文件尚不存在，先从命令中去掉该项。提交说明改成自己本次实际完成的内容。

~~~text
git add config/yarn/ tests/yarn-mapreduce/ docs/modules/yarn-mapreduce/
git diff --cached --stat
git commit -m "feat(yarn-mapreduce): complete module implementation and validation"
git push -u origin feat/yarn-mapreduce
~~~

核对没有误加他人的文件、日志或编译产物再 commit。首次提交若提示身份未配置，按提示设置本仓库的 git config user.name 和 git config user.email。推送报权限错误时，确认已接受组长的仓库邀请并登录自己的 GitHub 账号。

3. 打开 [仓库 PR 页面](https://github.com/deep-hang/hadoop/pulls)，点击 New pull request：**base 选 main，compare 选 feat/yarn-mapreduce**。
4. 检查 Files changed，点击 Create pull request。写清做了什么、运行命令、实际测试结果和未完成项；未测试通过的工作使用 Draft，暂不申请合并。
5. 等组长审核。收到修改意见后，仍在 feat/yarn-mapreduce 修改、复测，再重复第 2 步；原 PR 会自动更新，不用另建 PR。
6. 组长复验后批准并点击 Merge pull request，代码才进入 main。成员不直接推送 main，也不自行合并 PR。

**需要获取其他成员已合入的代码时**：先在自己的分支提交保存修改，确认 git status 干净，再执行：

~~~text
git fetch origin
git merge origin/main
~~~

有冲突时联系相关负责人解决，重新测试后 git push。此过程保留自己的功能分支；后续继续开发仍用 feat/yarn-mapreduce，不用重复 git switch -c。更多说明见 [协作规则](../../contributing.md)。
