# 7 号：MergeFile 多文件合并

用 Java MapReduce 把 HDFS 上多个文本文件合并成一份**有序、去重、带来源**的结果。

- 模块代码、脚本和测试数据：本目录
- 测试脚本与多文件演示数据集：[../../tests/mergefile/](../../tests/mergefile/)
- 合并规则、实测记录和材料链接：[../../docs/modules/mergefile/](../../docs/modules/mergefile/)
- 公共接口约定（脚本参数、退出码约定）：[../../docs/interfaces.md](../../docs/interfaces.md)

## 1. 合并规则

下面的规则是**本组的设计方案**（老师未指定这些细节），已写进
[docs/modules/mergefile/](../../docs/modules/mergefile/) 供组长确认。

| 问题 | 本模块的做法 |
| --- | --- |
| “合并”指什么 | 把每个输入文件的每一行当作一条“记录”，按记录内容合并成一份全局结果，**不是简单拼接** |
| 是否去重 | **去重**。同一条记录在结果里只出现一行 |
| 是否排序 | **排序**。按记录内容的 UTF-8 字节序升序 |
| 是否保留来源 | **保留**。第三列是该记录出现过的来源文件名列表（去重、字典序） |
| 空行 | 空行、只含空白字符的行**直接丢弃**，不参与合并 |
| 首尾空白 | **去掉**每行首尾空白；行内空白保留，所以 `a b` 与 `a  b` 是两条不同记录 |
| 大小写 | **区分**大小写，`Apple` 与 `apple` 是两条不同记录 |
| 换行符 | CRLF 与 LF 视为同一行（行尾的 `\r` 随首尾空白一起去掉） |
| 输出文件数 | **一个**结果文件 `<output>/merged.txt`，外加作业自带的 `_SUCCESS` 标记 |
| Reducer 数量 | **固定 1 个**，用于保证全局有序和单一结果文件 |

### 输出格式

每行三个字段，用制表符（Tab）分隔：

```text
记录<TAB>次数<TAB>来源文件1,来源文件2,...
```

例：`apple<TAB>3<TAB>a.txt,b.txt,c.txt`

### 为什么固定用一个 Reducer

排序必须在**键与比较规则**里定义，不能依赖目录枚举顺序，也不能指望 Mapper 输出顺序。
本模块把记录本身当作键，交给 Reducer 汇总；因为一个键的全部取值必然汇聚到同一个 Reducer，
只要 Reducer 只有一个，输出天然就是全局有序的，代价是 Shuffle 阶段的数据都汇到一台机器上。

数据量大时的取舍：本模块的作业面向“多文件合并”这个演示场景，单个 Reducer 便于演示与核对；
若后续要处理很大的输入，可以改成“先按记录分桶到多个 Reducer，再对每个桶内部排序”的两阶段方案。
需要哪种规模由组长按课程要求决定。

## 2. 目录结构

```text
apps/mergefile/
├── build.sh                 编译：javac + jar，产物在 build/
├── run.sh                   运行：run.sh <input> <output>
├── verify.sh                核对：verify.sh <output>
├── expected/
│   └── merged-small.txt     固定小样例的唯一预期
├── input/                   固定小样例的输入（a.txt / b.txt / c.txt）
└── src/com/example/mergefile/
    ├── MergeFileDriver.java     Driver：参数检查、作业配置
    ├── MergeFileMapper.java     Mapper：规范化每一行，输出 记录 -> 次数+来源
    ├── MergeFileCombiner.java   Combiner：Map 端局部合并（与 Reducer 同逻辑）
    ├── MergeFileReducer.java    Reducer：汇总同一记录的全部出现
    └── MergeFileValues.java     值的编码/解码（次数 + 来源文件列表）
```

源码在 `src/` 下，编译产物 `build/` 不提交 Git。

## 3. 三个脚本怎么用

三个脚本都要在 Linux 容器里用 Bash 运行，并且会自己定位所在目录，从任何当前目录调用都可用。

### 3.1 编译

```bash
bash /workspace/apps/mergefile/build.sh
```

用 `hadoop classpath --glob` 拿类路径，用 `javac` 编译、用 `jar` 打包，产物是
`apps/mergefile/build/mergefile.jar`。清单里不写 `Main-Class`，因为
`hadoop jar <jar> <主类> <参数>` 在清单没有 `Main-Class` 时才会把第一个参数当作主类，
与官方 examples 的调用方式一致。

| 退出码 | 含义 |
| --- | --- |
| 0 | 编译成功 |
| 1 | 编译失败（找不到 javac/jar/hadoop、拿不到 classpath、源码有语法错误等） |

### 3.2 运行

```bash
bash /workspace/apps/mergefile/run.sh <input> <output>
```

`<input>` 是 HDFS 目录（内含多个文本文件）或单个文本文件，`<output>` 是**必须还不存在**的输出目录。
输出目录已存在时脚本直接失败，不会删除用户已有数据；换一个新输出目录即可再次运行。

运行成功后输出目录里有两个文件：

```text
<output>/merged.txt     合并结果
<output>/_SUCCESS       作业成功标记
```

| 退出码 | 含义 |
| --- | --- |
| 0 | 作业成功，结果文件已就位 |
| 2 | 参数错误（参数个数不对、输入与输出相同） |
| 3 | 环境问题（没编译、找不到 `hadoop` / `hdfs`、访问不了 HDFS） |
| 4 | 输入路径不存在 |
| 5 | 输出路径已存在 |
| 6 | MapReduce 作业执行失败 |
| 7 | 输出目录结构不对（缺 `_SUCCESS`、结果文件数量不对、重命名失败） |

### 3.3 核对

```bash
bash /workspace/apps/mergefile/verify.sh <output>
```

`verify.sh` 按上面第 1 节的规则核对**固定小样例**的输出，依次检查：

1. 输出目录存在；
2. 有 `_SUCCESS`，有 `merged.txt`，没有残留的 `part-r-*` 文件；
3. 内容与 `apps/mergefile/expected/merged-small.txt` **逐字节**一致（顺序敏感）；
4. 每行都是 3 个制表符分隔的字段；
5. 没有重复记录；
6. 记录按 UTF-8 字节序升序；
7. 记录行数、唯一记录数、出现次数合计、单条最大次数、重复记录条数、跨文件重复条数
   与固定预期逐项一致，并要求存在跨文件重复记录。

| 退出码 | 含义 |
| --- | --- |
| 0 | 全部通过 |
| 2 | 参数错误 |
| 3 | 环境问题（缺预期文件、找不到 `hdfs`） |
| 4 | 输出目录不存在，或缺 `_SUCCESS` / `merged.txt` |
| 5 | 内容与固定预期不一致（会打印 diff） |

> `verify.sh` 只认固定小样例。多文件演示数据集用另一份预期和另一个脚本核对，
> 见 [tests/mergefile/README.md](../../tests/mergefile/README.md)。
> 两个脚本的职责不能互换，也不要把小样例的答案套到大数据上。

## 4. 固定输入与固定预期

固定小样例在 `apps/mergefile/input/`，共 3 个文件、12 行：

```text
a.txt（4 行）
apple
banana
            <- 空行
cherry

b.txt（3 行）
banana
date
apple

c.txt（5 行）
  banana    <- 行首行尾各两个空格
Apple
apple
            <- 空行
date
```

固定预期在 `apps/mergefile/expected/merged-small.txt`，共 5 行：

```text
Apple	1	c.txt
apple	3	a.txt,b.txt,c.txt
banana	3	a.txt,b.txt,c.txt
cherry	1	a.txt
date	2	b.txt,c.txt
```

对应的 MapReduce 计数：`Map input records=12`、`Map output records=10`、
`Reduce input groups=5`、`Reduce output records=5`、`Shuffled Maps =3`。

## 5. 本地调试（不需要集群）

集群还没就绪时，可以在公共开发容器里用本地文件系统先验证逻辑：

```bash
bash /workspace/apps/mergefile/build.sh
bash /workspace/tests/mergefile/run-tests.sh
```

`run-tests.sh` 默认是本地模式（`file://` 文件系统 + local JobRunner），会跑完全部用例并打印
逐条 PASS/FAIL。**本地模式通过不等于真实 YARN 通过**，真实集群上的结果见
[docs/modules/mergefile/](../../docs/modules/mergefile/) 的实测记录。

## 6. 相关测试

| 脚本 | 作用 |
| --- | --- |
| [tests/mergefile/run-tests.sh](../../tests/mergefile/run-tests.sh) | 模块全部用例，支持 `--local`（默认）和 `--hdfs` |
| [tests/mergefile/verify-multi.sh](../../tests/mergefile/verify-multi.sh) | 核对多文件演示数据集的结果 |
| [tests/mergefile/run-cluster-demo.sh](../../tests/mergefile/run-cluster-demo.sh) | 起三节点集群，跑作业并收集两个 worker 的证据 |
| [tests/mergefile/check-example-jar.sh](../../tests/mergefile/check-example-jar.sh) | 核对官方 examples JAR 里没有 MergeFile 示例 |
