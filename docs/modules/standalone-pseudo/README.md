# 5 号：单机与伪分布式

**已经实现的启动和使用方法**见 [两种模式使用说明](README-RUNTIME.md)。自动测试见 [单机测试](../../../tests/standalone/) 和 [伪分布式测试](../../../tests/pseudo/)。下面保留本模块的分工与设计要求，日常运行优先按使用说明操作。

## 1. 你要完成什么

交付两套可区分、可复现的运行方式：单机模式用本地文件执行 Hadoop 作业；伪分布式在一个节点里运行独立的 NameNode/DataNode 进程，完成 HDFS 操作。两者不能只展示“进入了 Docker”。

## 2. 在哪里改

| 位置 | 内容 |
| --- | --- |
| modes/standalone/ | 单机配置、运行入口、输入与说明 |
| modes/pseudo/ | 伪分布式配置、编排、服务启动与停止入口 |
| tests/standalone/、tests/pseudo/ | 两种模式各自的验证脚本 |
| 本目录 | 两模式对比、实验步骤、结果、截图、PPT/视频链接 |

模式专用配置放自己的目录，不改 3、4 号的完全分布式配置。仍使用原基础镜像；节点、卷、Compose 项目名和宿主机端口与完全分布式隔离。

## 3. 单机模式怎么做

1. 通过公共环境验证，在 feat/standalone-pseudo 开发。用原开发容器开始实现。
2. 在 modes/standalone/ 准备固定输入及独立配置：fs.defaultFS=file:///，mapreduce.framework.name=local；不启动 HDFS/YARN。
3. 编写运行入口，明确加载自己的配置，输出写到忽略的 runtime/ 下；不要依赖别人电脑已有的文件。
4. 先在开发容器运行下方官方示例了解流程，再把配置、输入和命令整理成你自己的可复现入口。
5. 添加结果核对和输出已存在时的失败检查；更新 modes/standalone/README.md。

以下是**现在可在公共开发容器内执行的单机练习**，使用未改动的基础配置；这不是你最终交付的脚本：

~~~bash
mkdir -p /workspace/runtime/standalone-demo/input
printf 'hello hadoop\nhello\n' > /workspace/runtime/standalone-demo/input/sample.txt
hadoop jar /opt/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar wordcount /workspace/runtime/standalone-demo/input /workspace/runtime/standalone-demo/output-001
cat /workspace/runtime/standalone-demo/output-001/part-r-*
~~~

预期 hadoop=1、hello=2，无 YARN application ID。重复执行换 output-002 等新目录。

## 4. 伪分布式怎么做

1. 在 modes/pseudo/ 新建专用 Compose 和配置。一个容器内运行 NameNode、DataNode；fs.defaultFS 指向该容器，副本数为 1，持久卷独立。
2. 先只打通 HDFS：首次显式格式化空目录，然后启动两个进程。使用本地守护进程命令，编写停止与退出处理；不照搬需要 SSH 的 start-dfs.sh。
3. 公共 hadoop-node.sh 的 master/worker 分别面向三节点组合，不能直接当作单容器伪分布式完整入口。可参考其初始化保护和进程清理，模式专用脚本放 modes/pseudo/。
4. 检查 jps 有 NameNode、DataNode，dfsadmin -report 有 1 个 Live DataNode。完成 mkdir、put、ls、cat；在自己的 Web 端口查看节点。
5. 配合单节点 HDFS，可先用本地 MapReduce 执行示例；若增加单节点 YARN，需显式配置并启动 ResourceManager/NodeManager，再验证 1 个 RUNNING 节点。说明里写清实际使用哪一种计算方式。
6. 重启自己的伪分布式环境，读回原文件；确认不影响完全分布式卷与端口。
7. 在 modes/pseudo/README.md 补上从电脑终端启动、进入、验证、重启、停止的完整命令。**目前这些入口尚待你实现，不要引用不存在的脚本让其他人运行。**

建议宿主机 Web 端口使用 19870（NameNode）、如启用 YARN 则用 18088，并在自己的编排和说明中一致记录，绑定 127.0.0.1。

## 5. 怎样算完成

- 单机：固定本地输入 → Hadoop 作业 → 正确本地输出，不连接三节点。
- 伪分布式：单节点 HDFS 注册、文件读写、独立持久化和重启验证通过。
- 两套入口、测试和说明都能由他人复现，清楚区分文件系统、进程数、节点数与计算方式。
- PPT/视频分别演示两套配置和结果，再对比完全分布式；本目录记录命令、截图及材料链接。
- 按 [协作规则](../../contributing.md) 提 PR 到 main。

参考：[Hadoop 官方单节点说明](https://hadoop.apache.org/docs/r3.3.6/hadoop-project-dist/hadoop-common/SingleCluster.html)。

<a id="submit"></a>
## 测试成功后，怎样交给组长

以下 Git 命令在**电脑终端、项目根目录**执行；还在容器里时先输入 exit。提交 PR 就是申请合并，不会立即改动 main。

1. 执行下面两条，确认当前分支显示 feat/standalone-pseudo，并检查本次修改。显示 main 时先切回自己的分支；不要在 main 提交模块代码。

~~~text
git branch --show-current
git status
~~~

2. 把本模块文件加入提交，查看文件清单，再保存、推送。下面路径须已完成创建；如某文件尚不存在，先从命令中去掉该项。提交说明改成自己本次实际完成的内容。

~~~text
git add modes/standalone/ modes/pseudo/ tests/standalone/ tests/pseudo/ docs/modules/standalone-pseudo/
git diff --cached --stat
git commit -m "feat(standalone-pseudo): complete module implementation and validation"
git push -u origin feat/standalone-pseudo
~~~

核对没有误加他人的文件、日志或编译产物再 commit。首次提交若提示身份未配置，按提示设置本仓库的 git config user.name 和 git config user.email。推送报权限错误时，确认已接受组长的仓库邀请并登录自己的 GitHub 账号。

3. 打开 [仓库 PR 页面](https://github.com/deep-hang/hadoop/pulls)，点击 New pull request：**base 选 main，compare 选 feat/standalone-pseudo**。
4. 检查 Files changed，点击 Create pull request。写清做了什么、运行命令、实际测试结果和未完成项；未测试通过的工作使用 Draft，暂不申请合并。
5. 等组长审核。收到修改意见后，仍在 feat/standalone-pseudo 修改、复测，再重复第 2 步；原 PR 会自动更新，不用另建 PR。
6. 组长复验后批准并点击 Merge pull request，代码才进入 main。成员不直接推送 main，也不自行合并 PR。

**需要获取其他成员已合入的代码时**：先在自己的分支提交保存修改，确认 git status 干净，再执行：

~~~text
git fetch origin
git merge origin/main
~~~

有冲突时联系相关负责人解决，重新测试后 git push。此过程保留自己的功能分支；后续继续开发仍用 feat/standalone-pseudo，不用重复 git switch -c。更多说明见 [协作规则](../../contributing.md)。
