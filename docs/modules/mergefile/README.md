# 7 号：MergeFile 多文件合并

## 1. 你要完成什么

设计并实现 Java MapReduce 多文件合并：多个输入文件进入 HDFS，由集群执行 MapReduce 后输出约定的合并结果。需要同时展示数据分布和计算分布。

**组长已决定先由 7 号提出方案。** 建议 10 月 22 日前把是否去重/排序、空行规则、输出文件数、参考来源、固定输入与唯一预期写在本目录，提交方案 PR，组长确认后再实现。老师未指定细节，不能把本组设计写成老师原话。

当前 Hadoop 3.3.6 的 examples JAR 没有名为 MergeFile 的示例类，不要尝试一个假定存在的 mergefile 子命令。老师所指实例与实现来源由本方案说明，必要时核对课程参考资料。

## 2. 在哪里改

- apps/mergefile/src/：Mapper、Reducer（如设计需要）、Driver。
- apps/mergefile/input/：多个小型测试文件。
- apps/mergefile/build.sh、run.sh、verify.sh（新建）：编译、执行和核对结果。
- tests/mergefile/：多文件、边界和失败用例；apps/mergefile/README.md 写使用方法。
- 本目录：规则、固定预期、实验结果、截图、PPT/视频链接。

## 3. 按什么顺序做

1. 通过公共环境验证，在 feat/mergefile 开发。阅读 [应用接口](../../interfaces.md)。
2. 对照老师实例，写明：只是拼接还是要去重？是否排序？是否保留来源？“合并”指一个逻辑结果还是必须一个数据文件？把一组输入与唯一预期发给组长确认，再按该规则实现。
3. 准备至少两个输入文件，包含跨文件重复行、空行等边界。在规则未确认前可先做编译框架，不把自定结果写成正式验收标准。
4. 设计 Mapper/Reducer/Driver，使用 MapReduce 处理多文件输入；如果需要顺序，必须在键与比较规则中定义，不能依赖目录枚举或 Mapper 完成顺序。明确是否需要单个 Reducer 及其性能影响。
5. 写 build.sh：使用 javac、jar 和 hadoop classpath，产物放模块 build/。写 run.sh <input> <output>：接收 HDFS 路径，已有输出则失败。写 verify.sh <output>：按确认的规则核对全部输出及记录数/重复情况，失败返回非零。
6. 在公共开发容器先完成源码编译及局部逻辑测试；HDFS/YARN 未就绪时不要卡着等，也不要声称真实分布式已通过。
7. 等 2—4 号交付后同步 main，从 master 提交应用；先跑固定小样本，再用多文件/合理分片展示两个 worker 的存储和计算参与。
8. 与 3 号核对 fsck 的块位置，与 4 号核对真实 application 和任务节点；把命令、预期、结果整理到 tests/mergefile/ 和本目录。

## 4. 先怎样设计测试

例如 a.txt 为 apple、banana 两行，b.txt 为 banana、cherry 两行。若保留重复应有 4 条记录，若去重应有 3 条；是否排序还会影响预期顺序。这只是帮助确认规则的例子，**不是已确定的课程要求**。

至少验证：多文件正常输入、跨文件重复、空文件/空行、输入不存在、输出已存在。空输入的成功/失败行为也需写明。verify 不能只判断产生了文件。

## 5. 脚本实现后怎样跑

**前提：规则已确认、应用脚本已完成、正式集群就绪。** 从电脑终端按 [2 号说明](../distributed/README.md) 进入 master，以下在容器内执行：

~~~bash
bash /workspace/apps/mergefile/build.sh
hdfs dfs -mkdir -p /project/input/mergefile
hdfs dfs -put /workspace/apps/mergefile/input/*.txt /project/input/mergefile
hdfs fsck /project/input/mergefile -files -blocks -locations
bash /workspace/apps/mergefile/run.sh /project/input/mergefile /project/output/mergefile/run-001
bash /workspace/apps/mergefile/verify.sh /project/output/mergefile/run-001
hdfs dfs -ls /project/output/mergefile/run-001
~~~

verify.sh 默认核对已确认的小样例；多 Worker 演示使用独立数据目录，在 tests/mergefile/ 给出相应预期及核对命令，不把小样例答案套到大数据。输入已上传则不重复 put；再次演示换新的输出目录。查看内容的命令应按实际产物在模块 README 中写明。不能用 hdfs dfs -getmerge 在电脑上拼接文件来替代本模块的 MapReduce 实现。

## 6. 怎样算完成

合并规则和固定预期清楚；三个应用脚本按公共接口工作；多文件结果正确；真实 YARN 作业成功，并有两个 worker 的数据与计算证据。不要为了单文件输出而误称只有一个 worker 也算分布式参与证明。

## 7. 本组确定的合并规则

下面的规则是**本组的设计方案**，老师未指定这些细节。已写进
[apps/mergefile/README.md](../../apps/mergefile/) 并提交组长确认；确认前不作为老师原话使用。

| 组长需要说清的事 | 本方案 |
| --- | --- |
| 拼接还是去重 | **去重**，次数累加到第二列 |
| 是否排序 | **排序**，按记录内容的 UTF-8 字节序升序 |
| 是否保留来源 | **保留**，第三列是来源文件名列表（去重、字典序） |
| 空行规则 | 空行、纯空白行丢弃；去掉首尾空白；**行内空白保留** |
| 一个逻辑结果还是一个数据文件 | 两者都要：全局去重有序，落成单个 `merged.txt` |
| 参考来源 | Hadoop 3.3.6 examples JAR **无** `MergeFile` 类（`check-example-jar.sh` 已核实），最接近的官方写法是 `MultiFileWordCount` |

输出格式：`记录<TAB>次数<TAB>来源文件1,来源文件2,...`。排序靠"键 = 记录本身"加单个 Reducer 实现，
不依赖目录枚举顺序，也不依赖 Mapper 完成顺序。

固定小样例的输入在 `apps/mergefile/input/`，唯一预期在 `apps/mergefile/expected/merged-small.txt`：

```text
Apple	1	c.txt
apple	3	a.txt,b.txt,c.txt
banana	3	a.txt,b.txt,c.txt
cherry	1	a.txt
date	2	b.txt,c.txt
```

## 8. 实测记录

两轮都在 **Windows 10 + Docker Desktop + `hadoop-base:v0.1`（Hadoop 3.3.6 / Temurin JDK 1.8.0_442）** 上跑通。

| 测试套件 | 环境 | 结果 |
| --- | --- | --- |
| `tests/mergefile/run-tests.sh` | 本地模式（`file://` + local JobRunner） | 48 项断言全部通过，`RESULT: PASS` |
| `tests/mergefile/run-tests.sh --hdfs` | 真实三节点集群（HDFS + YARN） | 48 项断言全部通过，`RESULT: PASS` |
| `check-scripts.sh` | 13 个脚本换行符与 shebang | 通过 |
| `check-fixtures.sh` | 演示数据集可重复生成 | 通过（重生成哈希与提交版本一致） |
| `check-example-jar.sh` | 官方 examples JAR 检查 | 通过（确认无 `MergeFile` 类） |

复现命令（开发容器内，本地模式）：

```bash
bash /workspace/tests/mergefile/run-tests.sh
```

复现命令（集群 master 容器内，HDFS 模式）：

```bash
bash /workspace/tests/mergefile/run-cluster-tests.sh
```

真实集群上的两个作业均为 `FINISHED / SUCCEEDED`：

| 作业 | 输入 | Map | Reduce | 结果 |
| --- | --- | --- | --- | --- |
| `application_1792936414411_0009` | `apps/mergefile/input/` 3 个文件 | 3 个（`Data-local map tasks=3`） | 1 个 | 12 行输入 → 10 条记录 → 5 条唯一记录，与固定预期逐字节一致 |
| `application_1792936414411_0010` | `tests/mergefile/input-multi/` 8 个文件 | 8 个（`Data-local map tasks=8`） | 1 个 | 56 行输入 → 40 条记录 → 11 条唯一记录，与 `expected/multi-expected.txt` 逐字节一致 |

集群模式下 `run-tests.sh --hdfs` 的输出保留在 `/project/output/mergefile-test/run-<时间戳>/`，脚本不会删除已有数据。

## 9. 两个 Worker 的数据与计算证据

**数据分布**：`hdfs fsck /project/input/mergefile-multi -files -blocks -locations` 显示 8 个输入文件的块
同时存放在 worker1（172.19.0.2）与 worker2（172.19.0.4）上，副本数 2，`Status: HEALTHY`，无缺块。

**计算分布**：逐节点核对容器目录，任务类型从容器自己的 `syslog` 判断，不靠容器编号猜测。

| 作业 | worker1 | worker2 |
| --- | --- | --- |
| 8 文件作业 `..._0010` | 4 个 Map 任务 + Reduce 任务 | 4 个 Map 任务 |
| 3 文件作业 `..._0009` | 1 个 Map 任务 | 2 个 Map 任务 + Reduce 任务 |

两个 worker 都有 Map 任务实跑，**不是**"两个节点在线就算参与"。收集命令：

```bash
bash tests/mergefile/run-cluster-demo.sh          # 起集群、跑作业、收证据、拆集群
bash tests/mergefile/collect-evidence.sh <项目名>  # 单独收集证据
```

## 10. 与任务要求的逐条对照

| 任务要求（第 3 节） | 本模块的完成情况 |
| --- | --- |
| 明确是否去重、是否排序、是否保留来源、合并是逻辑结果还是数据文件 | 第 7 节表格逐项写明，供组长确认 |
| 至少两个输入文件，包含跨文件重复行、空行等边界 | 固定小样例 3 个文件共 12 行（跨文件重复、空行、首尾空白、大小写）；演示数据集 8 个文件 56 行 |
| 排序必须定义在键与比较规则中，不能依赖目录枚举或 Mapper 顺序 | 键 = 记录本身，固定 1 个 Reducer，输出天然全局有序 |
| 明确是否需要单个 Reducer 及其性能影响 | 第 7 节说明取舍与大数据量的两阶段替代方案 |
| build.sh 用 javac、jar、hadoop classpath，产物放 build/ | 已实现，产物 `apps/mergefile/build/mergefile.jar` |
| run.sh 接收 HDFS 路径，已有输出则失败 | 已实现，输出已存在返回 5 |
| verify.sh 按确认规则核对全部输出及记录数/重复情况，失败返回非零 | 已实现，逐字节比对 + 记录数核对；被破坏的输出能被识别 |
| 不能用 `hdfs dfs -getmerge` 替代本模块的 MapReduce 实现 | 全流程只用 MapReduce 作业，无 getmerge |
| 在公共开发容器先编译并做局部测试 | 已完成，本地模式 48 项断言通过 |
| 从 master 提交应用，先跑固定小样本再用多文件展示两个 worker | 已完成，两批输入均为真实 YARN 作业且 `SUCCEEDED` |
| 与 3 号核对 fsck 块位置，与 4 号核对真实 application 和任务节点 | 第 9 节记录了块位置与容器所在节点 |

## 11. 仍待完成

1. **组长确认规则**：第 7 节明确标注为本组方案而非老师原话；规则若调整，需同步改代码、固定预期与测试。
2. **截图与 PPT/视频链接**：按"合并目的 → 输入规则 → MapReduce 设计 → 上传 → 数据位置 → 作业 → 任务节点 → 输出验证"的顺序准备。
3. **正式集群复核**：当前用的是公共验证配置 `tests/common/fixtures/cluster/`，2 号的正式编排交付后用同一组命令再跑一遍。

PPT/视频讲清合并目的、输入规则、MapReduce 设计，再演示上传 → 数据位置 → 作业 → 任务节点 → 输出验证。本目录补实测记录和材料链接，按 [协作规则](../../contributing.md) 提 PR 到 main。

<a id="submit"></a>
## 测试成功后，怎样交给组长

以下 Git 命令在**电脑终端、项目根目录**执行；还在容器里时先输入 exit。提交 PR 就是申请合并，不会立即改动 main。

1. 执行下面两条，确认当前分支显示 feat/mergefile，并检查本次修改。显示 main 时先切回自己的分支；不要在 main 提交模块代码。

~~~text
git branch --show-current
git status
~~~

2. 把本模块文件加入提交，查看文件清单，再保存、推送。下面路径须已完成创建；如某文件尚不存在，先从命令中去掉该项。提交说明改成自己本次实际完成的内容。

~~~text
git add apps/mergefile/ tests/mergefile/ docs/modules/mergefile/
git diff --cached --stat
git commit -m "feat(mergefile): complete module implementation and validation"
git push -u origin feat/mergefile
~~~

核对没有误加他人的文件、日志或编译产物再 commit。首次提交若提示身份未配置，按提示设置本仓库的 git config user.name 和 git config user.email。推送报权限错误时，确认已接受组长的仓库邀请并登录自己的 GitHub 账号。

3. 打开 [仓库 PR 页面](https://github.com/deep-hang/hadoop/pulls)，点击 New pull request：**base 选 main，compare 选 feat/mergefile**。
4. 检查 Files changed，点击 Create pull request。写清做了什么、运行命令、实际测试结果和未完成项；未测试通过的工作使用 Draft，暂不申请合并。
5. 等组长审核。收到修改意见后，仍在 feat/mergefile 修改、复测，再重复第 2 步；原 PR 会自动更新，不用另建 PR。
6. 组长复验后批准并点击 Merge pull request，代码才进入 main。成员不直接推送 main，也不自行合并 PR。

**需要获取其他成员已合入的代码时**：先在自己的分支提交保存修改，确认 git status 干净，再执行：

~~~text
git fetch origin
git merge origin/main
~~~

有冲突时联系相关负责人解决，重新测试后 git push。此过程保留自己的功能分支；后续继续开发仍用 feat/mergefile，不用重复 git switch -c。更多说明见 [协作规则](../../contributing.md)。
