# 资源管理、作业提交与双 NodeManager 测试

负责人：4 号。本目录验证三节点集群上的 YARN 注册、真实 MapReduce 作业、结果正确性和两个 worker 的任务参与。

## 1. 前置条件

- 2 号的正式三节点集群已启动，`master`、`worker1`、`worker2` 在同一网络；
- 三个节点都已挂载 `config/yarn/yarn-site.xml`、`config/yarn/mapred-site.xml`；
- 3 号的 HDFS 已就绪，`hdfs dfsadmin -report` 显示 2 个 Live DataNode；
- 在**电脑终端、项目根目录**执行，已导入 `hadoop-base:v0.1` 镜像；
- 默认读取 2 号的 `compose/distributed.yaml` 和项目名 `hadoop-distributed`。

脚本不会启动、停止或格式化集群，只做只读检查、上传固定输入和提交作业。重复运行请让它自动生成新的输出目录，或显式传 `--output`。

## 2. 执行

```bash
python3 tests/yarn-mapreduce/check-yarn.py
```

等价于默认参数：

```text
--compose-file compose/distributed.yaml
--project hadoop-distributed
--input /project/input/yarn-check
--output /project/output/yarn-check/run-<时间戳>
```

在这台电脑上，2 号编排尚未合入时，可用 `runtime/yarn-lab/compose.yaml` 做预验证（该目录不提交）：

```bash
COMPOSE_FILE=runtime/yarn-lab/compose.yaml \
COMPOSE_PROJECT=hadoop-yarn-lab \
python3 tests/yarn-mapreduce/check-yarn.py
```

## 3. 检查内容与预期

| 检查 | 预期 |
| --- | --- |
| `yarn node -list` | 恰好 `worker1`、`worker2` 两个 `RUNNING` |
| HDFS | 2 个 Live DataNode，Safe mode 为 OFF |
| 固定输入 | 8 个文件，每个 1000 行 `hello hadoop`，共 8000 行 |
| 作业 | 输出真实 `application_<时间戳>_<序号>`，`State : FINISHED`、`Final-State : SUCCEEDED` |
| 结果 | 合计 `hadoop=8000`、`hello=8000`，多词、少词都失败 |
| 双 worker | `worker1`、`worker2` 各有至少一个**成功完成**的 `YarnChild` 任务（容器 `syslog` 含 `Task 'attempt_...' done.`）；失败、被杀、推测执行取消或未成功的重试容器会被忽略 |

作业使用 `-D mapreduce.job.reduces=2`，8 个 Map 加 2 个 Reduce，便于让两个 worker 都实际参与。脚本按容器类型（`launch_container.sh`/`syslog` 中的 `YarnChild`、`MRAppMaster`）和任务完成标志判断，不靠容器目录数量；`_000001` 是每个 application attempt 的 ApplicationMaster，重试 attempt 的 AM（如 `_02_000001`）也会被排除。失败、被杀或未成功的重试尝试只写入 `skipped`，不能证明该 worker 完成过任务。

## 4. 参数

| 参数 | 默认值 | 作用 |
| --- | --- | --- |
| `--compose-file` | `compose/distributed.yaml` 或 `COMPOSE_FILE` | 2 号编排文件，相对仓库根目录 |
| `--project` | `hadoop-distributed` 或 `COMPOSE_PROJECT` | Compose 项目名 |
| `--input` | `/project/input/yarn-check` | 固定 HDFS 输入目录，已存在且为 8 个文件时复用 |
| `--output` | 自动时间戳目录 | 输出目录，已存在时脚本拒绝执行 |
| `--wait` | 420 秒 | 等待双 DataNode、双 NodeManager 就绪 |
| `--job-timeout` | 1200 秒 | 单次作业超时，ARM 模拟环境按需加大 |

`--input` 和 `--output` 必须是绝对 HDFS 路径。空格、`$`、`&`、括号、中文等可以直接使用，调用时用引号包住整段路径；HDFS glob 字符 `* ? [ ] { }` 会在提交前被拒绝，避免把目录名误当成通配符。例如：

```bash
python3 tests/yarn-mapreduce/check-yarn.py \
  --input '/project/input/yarn check $demo & (测试)' \
  --output '/project/output/yarn check/run 001'
```

## 5. 失败用例

以下情况必须返回非零，脚本会打印具体原因：

- 集群没有启动，或只有 1 个 NodeManager；
- 输出目录已存在（保护已有数据，不自动删除）；
- 路径不是绝对 HDFS 路径，或含 `* ? [ ] { }`；
- 作业没有 application ID（说明退化成 local 模式）；
- `Final-State` 不是 `SUCCEEDED`；
- 词频与预期不一致；
- 只有一个 worker 有成功完成的任务，或两边只有 AM、失败/重试容器；
- NodeManager 重启后 userlogs 已被清理，读不到任务日志。

手工复现输出目录冲突：

```bash
python3 tests/yarn-mapreduce/check-yarn.py --output /project/output/yarn-check/existing
python3 tests/yarn-mapreduce/check-yarn.py --output /project/output/yarn-check/existing
```

第二次应失败并提示输出已存在。

## 6. 证据

每次执行写入 `runtime/yarn-check-<时间戳>/`（已被 `.gitignore` 忽略）：

- `result.json`：节点、application ID、词频、`worker_task_evidence`（成功任务、Map/Reduce 分类、被忽略的 AM/失败/重试容器）和 `worker_task_containers`（仅成功容器）、通过/失败状态；
- `NNN.log`：按顺序保存的每条 `docker compose` 命令、退出码和完整输出。

提交 PR 时把有代表性的命令和结果摘要写入 `docs/modules/yarn-mapreduce/README.md`，不要把日志或大截图提交进 Git。

## 7. 限制

- 2026-10-27 本机预验证通过：常规路径 `application_1793087201211_0001`（worker1/worker2 成功任务 4/6）；含空格和特殊字符的路径 `application_1793087201211_0002`（worker1 4 个成功 Map + 2 个被忽略的重试容器，worker2 4 Map + 2 Reduce），两次输出均为 8000/8000。使用的是 `runtime/yarn-lab/` 临时编排；
- NodeManager 重启会清理 `userlogs`，脚本必须在作业结束后立即读取；不能拿很久以前的 application ID 反复做证据检查；
- HDFS glob 字符 `* ? [ ] { }` 不作为字面目录名支持；
- 未启用 JobHistory Server 和日志聚合，所以用各 worker 的 `userlogs` 取证，而不是 `yarn logs`；
- 脚本假定服务名固定为 `master`、`worker1`、`worker2`，端口按公共契约；
- 测试不覆盖 2 号编排的启动、网络和持久卷，那些由 `tests/distributed/` 验证；
- 本机预验证使用公共 HDFS fixture，正式验收必须在 2、3 号合入后的集群上重跑。
