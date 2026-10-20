# 7 号：MergeFile 多文件合并

## 1. 你要完成什么

设计并实现 Java MapReduce 多文件合并：多个输入文件进入 HDFS，由集群执行 MapReduce 后输出约定的合并结果。需要同时展示数据分布和计算分布。

**先固定“合并”的规则，再写代码。** 当前课程材料中的 MergeFile 细节尚未明确，不能自行把某种去重或排序规则当成老师的要求。

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

输入已上传则不重复 put；再次演示换新的输出目录。查看内容的命令应按实际产物在模块 README 中写明。不能用 hdfs dfs -getmerge 在电脑上拼接文件来替代本模块的 MapReduce 实现。

## 6. 怎样算完成

合并规则和固定预期清楚；三个应用脚本按公共接口工作；多文件结果正确；真实 YARN 作业成功，并有两个 worker 的数据与计算证据。不要为了单文件输出而误称只有一个 worker 也算分布式参与证明。

PPT/视频讲清合并目的、输入规则、MapReduce 设计，再演示上传 → 数据位置 → 作业 → 任务节点 → 输出验证。本目录补实测记录和材料链接，按 [协作规则](../../contributing.md) 提 PR 到 main。
