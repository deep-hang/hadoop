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
for n in 01 02 03 04 05 06 07 08; do
  awk 'BEGIN { for (i = 0; i < 1000; i++) print "hello hadoop" }' \
    > "/tmp/yarn-demo/part-$n.txt"
done
hdfs dfs -mkdir -p /project/input/yarn-demo
hdfs dfs -put /tmp/yarn-demo/*.txt /project/input/yarn-demo
hadoop jar /opt/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar \
  wordcount -D mapreduce.job.reduces=2 \
  /project/input/yarn-demo /project/output/yarn-demo/run-001
hdfs dfs -cat '/project/output/yarn-demo/run-001/part-r-*'
yarn application -list -appStates ALL
~~~

预期两个 RUNNING 节点，任务有 application ID、最终成功，输出合计 `hadoop=8000`、`hello=8000`（两个 `part-r-*` 文件各一个词）。重复演示换新输出目录；已有输入不用重复 put。

在电脑浏览器打开 http://localhost:8088 查看作业。两个 worker 的 /opt/hadoop/logs/userlogs 中可查对应 application 的任务日志；区分 ApplicationMaster 与 Map/Reduce 容器，记录实际运行任务的节点。若只用了一个 worker，检查分片数量、资源余量和调度，再调整演示输入。

## 5. 怎样算完成

两节点注册、真实 YARN 作业成功、正确输出、两个 worker 都有**成功完成**的 Map/Reduce 任务尝试；记录 Docker 资源、YARN 资源及任务内存的关系。失败、被杀或重试未成功的容器不计入。

自动检查（推荐，在电脑终端、项目根目录执行）：

```bash
python3 tests/yarn-mapreduce/check-yarn.py
```

脚本自动完成节点注册、固定输入、真实作业、输出核对和双 worker 成功任务检查；它按容器类型和 `Task 'attempt_...' done.` 判断，不数目录，失败/重试尝试会被忽略。`--input`/`--output` 支持空格和 shell 特殊字符（调用时加引号），但拒绝 HDFS glob 字符 `* ? [ ] { }`。手工命令见第 4 节，本机实测见第 6 节。

PPT/视频讲清 ResourceManager、NodeManager、ApplicationMaster、Map/Shuffle/Reduce，按“配置 → 注册 → 提交 → 状态 → 节点任务 → 结果”演示。补好本目录实测记录，按 [协作规则](../../contributing.md) 提 PR 到 main。

参考：[MapReduce 官方教程](https://hadoop.apache.org/docs/r3.3.6/hadoop-mapreduce-client/hadoop-mapreduce-client-core/MapReduceTutorial.html)。

## 6. 本机预验证记录（2026-10-27）

> 这是 4 号本机的预验证，不是最终验收。2 号的 `compose/distributed.yaml` 和 3 号的 `config/hdfs/` 尚未合入 main，正式集群就绪后必须按第 4 节重跑，并用正式 application ID 替换本节记录。

### 6.1 环境

| 项目 | 实测值 |
| --- | --- |
| 电脑 | MacBook Pro，Apple Silicon（arm64），16 GB 内存 |
| Docker | Docker Desktop，Linux 容器，8 GB 虚拟机 / 9 CPU |
| 镜像 | `hadoop-base:v0.1`，linux/amd64，ID `sha256:45a1ee...`；发布包 SHA256 与 [验证记录](../../phase0-status.md) 一致 |
| 软件 | Java 1.8.0_442、Hadoop 3.3.6 |
| 加速 | Docker Desktop 启用 Rosetta（`useVirtualizationFrameworkRosetta=true`） |
| 编排 | `runtime/yarn-lab/compose.yaml`（本机临时文件，不提交）；HDFS 暂借 `tests/common/fixtures/cluster/` 配置 |

### 6.2 执行

```bash
COMPOSE_FILE=runtime/yarn-lab/compose.yaml \
COMPOSE_PROJECT=hadoop-yarn-lab \
python3 tests/yarn-mapreduce/check-yarn.py
```

退出码 0。证据在 `runtime/yarn-check-20261027-154803/` 和 `runtime/yarn-check-20261027-155904/`（`runtime/` 已被 `.gitignore` 忽略）。

### 6.3 结果

| 检查项 | 实测 |
| --- | --- |
| NodeManager | worker1、worker2 均 `RUNNING`，各 `memory:2048, vCores:2` |
| DataNode | 2 个 Live；`Under replicated blocks: 0` |
| Application | `application_1793087201211_0001`，`FINISHED` / `SUCCEEDED`，AM 在 worker2 |
| 作业时间 | 约 5 分 50 秒（本轮集群 RPC 较慢；同一配置更早一轮约 37 秒） |
| 输出 | `part-r-00000` 为 `hadoop 8000`，`part-r-00001` 为 `hello 8000` |
| 双 worker 成功任务 | worker1 4 个 Map；worker2 4 个 Map + 2 个 Reduce |
| 资源 | Aggregate 1177335 MB-seconds、2294 vcore-seconds |

每个 application attempt 的 `_000001` 都是 ApplicationMaster；脚本按 `MRAppMaster` 类型和 `_000001` 后缀排除，只统计 `YarnChild` 且带成功标志的任务。

### 6.4 失败用例

```bash
python3 tests/yarn-mapreduce/check-yarn.py \
  --output /project/output/yarn-check/run-20261027-154803
```

第二次执行返回非零，提示 `Output already exists, refusing to delete it`，没有删除已有结果。

### 6.5 关键结论

- 未启用 Rosetta 时，ResourceManager 在 QEMU 模拟下超过 10 分钟仍未完成启动；启用 Rosetta 后，同一镜像和配置能完成注册并跑完作业。Apple Silicon 必须开启该加速。
- 两个 worker 都有 `YarnChild` 且带 `Task 'attempt_...' done.` 的成功任务；节点在线截图或容器目录存在不能替代这项证据。
- 失败、被杀或重试未成功的容器没有该标志，只能算“尝试过”，不能算“完成过任务”。
- 512 MB 容器、384 MB 堆能装进 2048 MB NodeManager，调度和 Shuffle 正常。

### 6.6 重试与自定义路径复测

`application_1793087201211_0002` 使用含空格和 shell 特殊字符的输入、输出路径：

```bash
python3 tests/yarn-mapreduce/check-yarn.py \
  --input '/project/input/yarn check $demo & (测试)' \
  --output '/project/output/yarn check/run 001'
```

结果：作业成功，输出仍为 `hadoop=8000`、`hello=8000`。worker1 有 4 个成功 Map；另有 2 个容器（`..._01_000002`、`..._01_000013`）没有成功标志（失败、被杀或重试未成功），被记入 `skipped`，不再算作 worker1 的成功任务。worker2 有 4 个成功 Map 和 2 个成功 Reduce。该复测同时验证了空格、`$`、`&`、括号和中文路径。

### 6.7 待补

- 2、3 号合入后在正式集群重跑，记录正式 application ID、启动等待时间和截图；
- 8088 与 9870 页面截图；
- PPT 和带字幕配音视频链接。

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
