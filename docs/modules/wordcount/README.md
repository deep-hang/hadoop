# 6 号：WordCount 单词统计

## 1. 你要完成什么

实现自己的 Java MapReduce 单词统计：输入文本 → Mapper 输出“单词、1” → 按单词汇总 → Reducer 输出次数。最终在真实 HDFS/YARN 上运行并展示两个 worker 的任务参与。

## 2. 在哪里改

- apps/wordcount/src/：Mapper、Reducer、Driver 源码。
- apps/wordcount/input/：可提交的小型固定输入；大规模演示数据用生成方法，不提交巨型文件。
- apps/wordcount/build.sh、run.sh、verify.sh（新建）：编译、执行、核对。
- tests/wordcount/：正常与失败用例；apps/wordcount/README.md 写实际操作入口。
- 本目录：实例规则、流程、实测结果、截图和 PPT/视频链接。

## 3. 按什么顺序做

1. 通过公共环境验证，在 feat/wordcount 开发；先读 [应用接口](../../interfaces.md)。
2. 先固定分词规则：是否区分大小写、标点如何处理、空行是否忽略。写进模块 README，让输入、预期结果和代码一致。
3. 编写 Mapper、Reducer、Driver：Driver 接收输入和输出参数，设置各阶段类型与输入/输出路径；作业失败时返回非零。
4. 写 build.sh：用现有 javac、jar 编译打包到 apps/wordcount/build/，编译类路径从 hadoop classpath 获取。基础镜像没有 Maven。脚本自行定位目录，从其他当前目录调用也应有效。
5. 写 run.sh <input> <output> 与 verify.sh <output>。最终按 HDFS 路径解释；输出目录已存在则失败，不自动删数据。verify 核对实际内容，不能只检查 _SUCCESS 存在。
6. 上游未就绪时，在开发容器先完成编译、分词/汇总逻辑和固定预期；需要临时本地模式调试时写清调用方式，不把本地成功当作 YARN 成功。
7. 等 2—4 号通知集群就绪，按 [协作规则](../../contributing.md) 同步 main，进入 master 后完成下方流程。
8. 再扩大输入分片，记录两个 worker 的 Map/Reduce 任务证据；与 4 号一起处理调度和资源问题。

## 4. 固定输入与预期

建议先使用这两个文件：

~~~text
a.txt:
hello hadoop
hello

b.txt:
hadoop world
~~~

预期词频 hadoop=2、hello=2、world=1。verify.sh 读取全部 part-r-*，按词频比较，不依赖文件排列顺序。另测空行、约定的大小写/标点、输入不存在、输出已存在。

## 5. 脚本实现后怎样跑

**以下要求你的三个脚本已实现，且正式三节点就绪。** 从电脑终端按 [2 号说明](../distributed/README.md) 进入 master，以下在容器内逐条执行：

~~~bash
bash /workspace/apps/wordcount/build.sh
hdfs dfs -mkdir -p /project/input/wordcount
hdfs dfs -put /workspace/apps/wordcount/input/*.txt /project/input/wordcount
bash /workspace/apps/wordcount/run.sh /project/input/wordcount /project/output/wordcount/run-001
bash /workspace/apps/wordcount/verify.sh /project/output/wordcount/run-001
hdfs dfs -cat '/project/output/wordcount/run-001/part-r-*'
~~~

第一次运行先使用固定小输入。重复演示输入不用重复 put，输出换 run-002。verify.sh 默认核对上面的小样例。大规模测试使用独立输入/输出子目录，在 tests/wordcount/ 另提供与大数据匹配的预期和核对命令，不改公共脚本参数。

另外保留一次 Hadoop 官方自带 WordCount 的对照演示，命令见 [4 号指南](../yarn-mapreduce/README.md)。老师要求了自带实例的配置与演示；本组源码实现与官方演示都要说明清楚。

## 6. 怎样算完成

build、run、verify 成功与失败的退出码正确；小输入词频准确；真实 YARN application 成功，两个 worker 的计算参与有证据，不能仅截图节点在线。

PPT/视频讲清输入、Mapper、Shuffle、Reducer、Driver，再演示编译 → HDFS 输入 → 作业 → 节点任务 → 输出核对。本目录补真实命令与结果，按 [协作规则](../../contributing.md) 提 PR 到 main。

参考：[MapReduce 官方教程](https://hadoop.apache.org/docs/r3.3.6/hadoop-mapreduce-client/hadoop-mapreduce-client-core/MapReduceTutorial.html)。

<a id="submit"></a>
## 测试成功后，怎样交给组长

以下 Git 命令在**电脑终端、项目根目录**执行；还在容器里时先输入 exit。提交 PR 就是申请合并，不会立即改动 main。

1. 执行下面两条，确认当前分支显示 feat/wordcount，并检查本次修改。显示 main 时先切回自己的分支；不要在 main 提交模块代码。

~~~text
git branch --show-current
git status
~~~

2. 把本模块文件加入提交，查看文件清单，再保存、推送。下面路径须已完成创建；如某文件尚不存在，先从命令中去掉该项。提交说明改成自己本次实际完成的内容。

~~~text
git add apps/wordcount/ tests/wordcount/ docs/modules/wordcount/
git diff --cached --stat
git commit -m "feat(wordcount): complete module implementation and validation"
git push -u origin feat/wordcount
~~~

核对没有误加他人的文件、日志或编译产物再 commit。首次提交若提示身份未配置，按提示设置本仓库的 git config user.name 和 git config user.email。推送报权限错误时，确认已接受组长的仓库邀请并登录自己的 GitHub 账号。

3. 打开 [仓库 PR 页面](https://github.com/deep-hang/hadoop/pulls)，点击 New pull request：**base 选 main，compare 选 feat/wordcount**。
4. 检查 Files changed，点击 Create pull request。写清做了什么、运行命令、实际测试结果和未完成项；未测试通过的工作使用 Draft，暂不申请合并。
5. 等组长审核。收到修改意见后，仍在 feat/wordcount 修改、复测，再重复第 2 步；原 PR 会自动更新，不用另建 PR。
6. 组长复验后批准并点击 Merge pull request，代码才进入 main。成员不直接推送 main，也不自行合并 PR。

**需要获取其他成员已合入的代码时**：先在自己的分支提交保存修改，确认 git status 干净，再执行：

~~~text
git fetch origin
git merge origin/main
~~~

有冲突时联系相关负责人解决，重新测试后 git push。此过程保留自己的功能分支；后续继续开发仍用 feat/wordcount，不用重复 git switch -c。更多说明见 [协作规则](../../contributing.md)。

<a id="status"></a>
## 实现状态与配套文档

当前进度：**阶段一完成**（代码、三个脚本、测试用例、文档已提交到 feat/wordcount）；
**阶段二待联调**（真实 HDFS / YARN 上的 build / run / verify 与双 Worker 证据，需 2—4 号集群就绪）。

| 文档 | 内容 |
| --- | --- |
| [implementation.md](implementation.md) | 实例设计与实现说明：输入数据设计、分词规则、一条数据走完全程、四个类的职责、为什么用 Combiner、为什么 2 个 Reduce、退出码与安全设计 |
| [test-results.md](test-results.md) | 实际执行过的测试与结果；未执行的项标“待执行”，不预填通过 |
| [demo-script.md](demo-script.md) | PPT 12 页结构、视频录制顺序、可直接照念的讲解稿、截图清单 |
| [apps/wordcount/README.md](../../../apps/wordcount/README.md) | 实际操作入口：分词规则、三个脚本用法、完整演示命令 |
| [tests/wordcount/README.md](../../../tests/wordcount/README.md) | 测试用例清单、边界输入与预期、失败场景 |

已知环境情况：开发机 2026-10-30 尚未安装 WSL2 与 Docker Desktop，公共环境第 2 步之后的验证未完成，
因此本模块尚不能在本机运行 build/run/verify 的真实集群流程。
