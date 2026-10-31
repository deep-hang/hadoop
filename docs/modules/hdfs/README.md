# 3 号：HDFS 分布式存储

> 实测记录见 [results.md](results.md)：2026-10-31 在三节点真实集群上跑通，含 `HDFS_TEST_PASS`、`HDFS_PERSISTENCE_PASS` 与副本位置证据。

## 1. 你要完成什么

让 master 的 NameNode 管理两个 worker 的 DataNode，证明文件能上传、读取，数据块和副本确实在两个 worker 上，重启不丢文件。

## 2. 在哪里改

- config/hdfs/core-site.xml、hdfs-site.xml（新建）：HDFS 地址、数据目录、副本配置。
- tests/hdfs/：固定测试输入与读写、副本、重启验证。
- config/hdfs/README.md：配置含义和实际入口；本目录记录结果、截图、PPT、视频链接。
- Compose 挂载和卷由 2 号接入；不要直接改他的编排文件。

## 3. 按什么顺序做

1. 通过公共环境验证，在 feat/hdfs 开发。先看 [公共接口](../../interfaces.md) 和 [HDFS 测试配置](../../../tests/common/fixtures/cluster/hdfs-site.xml)。
2. 写 core-site.xml：fs.defaultFS 固定为 hdfs://master:9000。写 hdfs-site.xml：dfs.namenode.name.dir 为 /var/lib/hadoop/hdfs/namenode，dfs.datanode.data.dir 为 /var/lib/hadoop/hdfs/datanode，两个 worker 的实验副本数设为 2。
3. 把配置含义和挂载清单交给 2 号。以他提供的正式集群为运行环境，检查数据卷可写；使用公共脚本显式初始化，不手工反复格式化。
4. 进入 master，检查实际加载的配置和两个 DataNode 注册情况。
5. 准备固定输入，依次完成 mkdir、put、ls、cat 和内容核对，尽早通知 6、7 号存储已可用。
6. 再用 fsck 查看块位置，保存 worker1、worker2 的证据；配合 2 号重启，确认文件仍可读。
7. 把这些步骤写进 tests/hdfs/ 的测试脚本；错误、内容不一致或节点数不符时返回非零。

若配置与 2 号编排互相等待，先提交配套 Draft PR，按 [联合验证流程](../../member-onboarding.md#joint-check) 共同测试，再审核合入。

## 4. 怎样验证

**先等 2 号交付正式集群并接入你的配置**，按 [2 号说明](../distributed/README.md) 从电脑终端进入 master。以下命令均在 master 内执行：

~~~bash
hdfs getconf -confKey fs.defaultFS
hdfs getconf -confKey dfs.namenode.name.dir
hdfs getconf -confKey dfs.datanode.data.dir
hdfs dfsadmin -report
mkdir -p /tmp/hdfs-demo
printf 'hello hadoop\n' > /tmp/hdfs-demo/sample.txt
hdfs dfs -mkdir -p /project/input/hdfs-demo
hdfs dfs -put /tmp/hdfs-demo/sample.txt /project/input/hdfs-demo/sample-001.txt
hdfs dfs -ls /project/input/hdfs-demo
hdfs dfs -cat /project/input/hdfs-demo/sample-001.txt
hdfs fsck /project/input/hdfs-demo/sample-001.txt -files -blocks -locations
~~~

预期地址与目录符合公共接口，Live datanodes 为 2，cat 输出 hello hadoop。fsck 应显示健康文件及两个副本位置；必要时配合 dfsadmin -report 对照节点名/IP。在电脑浏览器打开 http://localhost:9870 查看 Live Nodes。

再次演示请用 sample-002.txt 等新文件名，避免覆盖。重启前后各读取一次原文件并比较内容；重启命令由 2 号提供，不删卷。

## 5. 怎样算完成

两个 DataNode、文件读写、两节点副本位置、重启持久化均有实测证据。小文件也可展示副本，但若讲解“多个数据块”，要准备大于实际块大小的输入并核对块数。

PPT/视频讲清 NameNode、DataNode、Block、Replication，再演示配置 → 注册 → 上传读取 → 块位置 → 重启读取。本目录补实测命令、输出及材料链接，按 [协作规则](../../contributing.md) 提 PR 到 main。

参考：[HDFS 官方命令](https://hadoop.apache.org/docs/r3.3.6/hadoop-project-dist/hadoop-hdfs/HDFSCommands.html)。

<a id="submit"></a>
## 测试成功后，怎样交给组长

以下 Git 命令在**电脑终端、项目根目录**执行；还在容器里时先输入 exit。提交 PR 就是申请合并，不会立即改动 main。

1. 执行下面两条，确认当前分支显示 feat/hdfs，并检查本次修改。显示 main 时先切回自己的分支；不要在 main 提交模块代码。

~~~text
git branch --show-current
git status
~~~

2. 把本模块文件加入提交，查看文件清单，再保存、推送。下面路径须已完成创建；如某文件尚不存在，先从命令中去掉该项。提交说明改成自己本次实际完成的内容。

~~~text
git add config/hdfs/ tests/hdfs/ docs/modules/hdfs/
git diff --cached --stat
git commit -m "feat(hdfs): complete module implementation and validation"
git push -u origin feat/hdfs
~~~

核对没有误加他人的文件、日志或编译产物再 commit。首次提交若提示身份未配置，按提示设置本仓库的 git config user.name 和 git config user.email。推送报权限错误时，确认已接受组长的仓库邀请并登录自己的 GitHub 账号。

3. 打开 [仓库 PR 页面](https://github.com/deep-hang/hadoop/pulls)，点击 New pull request：**base 选 main，compare 选 feat/hdfs**。
4. 检查 Files changed，点击 Create pull request。写清做了什么、运行命令、实际测试结果和未完成项；未测试通过的工作使用 Draft，暂不申请合并。
5. 等组长审核。收到修改意见后，仍在 feat/hdfs 修改、复测，再重复第 2 步；原 PR 会自动更新，不用另建 PR。
6. 组长复验后批准并点击 Merge pull request，代码才进入 main。成员不直接推送 main，也不自行合并 PR。

**需要获取其他成员已合入的代码时**：先在自己的分支提交保存修改，确认 git status 干净，再执行：

~~~text
git fetch origin
git merge origin/main
~~~

有冲突时联系相关负责人解决，重新测试后 git push。此过程保留自己的功能分支；后续继续开发仍用 feat/hdfs，不用重复 git switch -c。更多说明见 [协作规则](../../contributing.md)。
