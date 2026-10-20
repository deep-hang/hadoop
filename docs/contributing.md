# 小组协作规则

1. 群昵称改为“姓名 + 任务号”，例如“周建行 1”。
2. 从最新 main 创建自己的功能分支，命令见 [使用说明](platform-setup.md#task-branch)。PR 目标统一为 main。
3. 每人修改自己的目录；公共配置、镜像、脚本和跨模块变更先由组长协调。
4. 一次提交一个可验证功能。提交说明用“类型(模块): 具体内容”；公共变更新建 .changes/日期-任务号-主题.md，写原因、影响、验证和回滚方式，不把所有人的变更都追加到同一个文件。
5. 自己开发、自己测试；完成后推送自己的分支，向 main 提交 PR，不直接推送 main 或公共底座分支。
6. PR 写明改动、接口变化、执行过的测试与结果。测试未通过时保留草稿，组长审核后合并。
7. 每人提交本模块实验说明、PPT、含字幕配音的视频和讲解，交接要求见 [联调说明](member-onboarding.md)。

## 公共版本管理

当前镜像以 phase0-image-v0.1 预发布分发；main 为默认集成分支，v0.1-bootstrap 稳定标签尚未创建。升级公共环境需使用新镜像标签，记录镜像 ID。

需要回退时，在修复分支使用 git revert 回退具体提交并提 PR，不强推、不重写 main；代码、配置和镜像版本一起恢复。

## 文件放置

- 测试按 [tests/ 分工](../tests/README.md) 放入自己的子目录；实验材料按 [docs/modules/ 分工](modules/README.md) 存放。
- compose/bootstrap.yaml 属于 1 号；2 号新建独立集群文件。config/common/、config/hdfs/、config/yarn/ 分别由 1、3、4 号维护，不混写配置。
- apps/ 和 modes/ 已按模块分开，代码和运行入口仍放原目录；scripts/ 保留公共工具，模块专用脚本放自己的功能目录。

## 开工前：组长邀请成员

1. 收齐 2—7 号的 GitHub 用户名。
2. 仓库 Settings → Collaborators，按 GitHub 提示添加成员；成员接受邀请后才能向本仓库推送自己的分支。
3. 新成员先验证环境，再完成一次小改动的提交、推送和 PR，确认整个协作流程可用。没有写权限时不要推送公共分支或借用组长账号。

## PR 是什么、怎么提交

PR（Pull Request）就是“申请把自己的分支改动合并到公共分支”，提交 PR 不等于已经合并。

1. 在电脑终端、项目根目录执行 git branch --show-current 和 git status，确认在自己的 feat/... 分支。
2. 只把本模块文件加入本次提交。下面是 **6 号 WordCount 的示例**，其他成员改用自己的代码、测试和实验材料目录：

```text
git add apps/wordcount/ tests/wordcount/ docs/modules/wordcount/
git diff --cached --stat
git commit -m "feat(wordcount): describe the completed change"
git push -u origin HEAD
```

提交说明换成实际完成的内容；发现暂存了无关文件时先调整，不直接提交。第一次 commit 若提示缺少身份，先用 git config user.name 和 git config user.email 设置本仓库的姓名、提交邮箱，再重试。push 按 GitHub 提示认证，403 或 Permission denied 时检查登录账号和邀请是否已接受。

3. 打开 GitHub 仓库的 Pull requests，点击 New pull request。
4. base 选择 main，compare 选择自己的 feat/... 分支；在文件列表中核对改动范围。
5. 点击 Create pull request，写清做了什么、如何运行、测试结果和未完成项，等待组长审核。
6. 根据反馈在原功能分支修改并推送，原 PR 会自动更新；新增改动后需要重新审核。

## 上游合并后，怎么同步到自己的分支

组长通知公共分支已有需要的模块后，在电脑终端、自己的功能分支中操作：

1. 先提交本地正在做的修改，用 git status 确认工作区干净。
2. 执行下面命令，把已经合并的上游代码同步进自己的分支：

```text
git fetch origin
git merge origin/main
```

3. 出现冲突先联系相关负责人，不用 reset --hard 或强推处理；解决后重新验证，最后 git push。
4. 未合并的上游工作由组长协调联调，不擅自复制另一位成员的整个目录。

## 组长怎么审核

1. 打开 PR 的 Files changed，确认没有误改公共文件或他人目录，再按交接命令复验。
2. 有问题时提出修改意见；通过后用 Review changes → Approve → Submit review 批准。
3. 确认改动和测试无误，再用 Merge pull request 合并。PR 审批通过本身不等于自动合并。

公共分支启用 PR 审核和代码所有者审核；.github/CODEOWNERS 指定 @deep-hang 为所有文件的审核人。组员不能直接推送公共分支，修改必须经组长批准；新改动会使旧批准失效。禁止普通成员强制推送或删除公共分支。

main 和保留的 common/phase0-bootstrap 均启用上述保护；后续 PR 统一合入 main，旧分支不再作为日常集成入口。

仓库所有者保留管理员维护权限；自己的维护变更不能由本人给自己的 PR 审批，必要时可使用所有者维护权限。目录归属仍按模块约定执行，这些规则保护的是合入公共分支的过程。

目前 PR 没有自动构建/集群测试，审核要求只保证有人批准，不保证功能正确；组长仍须核对实际运行记录并按交接命令复现。

## 已下载旧分支的成员怎样切换

无需重新克隆或导入镜像。在电脑终端的项目根目录操作：

1. 执行 git status；有修改时先在自己的功能分支提交保存，再继续。
2. 执行 git fetch origin，获取 main。
3. 按当前情况选择：
   - 还在 common/phase0-bootstrap、尚未开始开发：执行 git switch --track origin/main，然后按使用说明创建自己的任务分支。本地 main 已存在时改用 git switch main，再执行 git pull --ff-only。
   - 已在自己的 feat/... 分支开发：保留该分支，执行 git merge origin/main；如有冲突联系负责人解决，再验证并 git push。
4. 后续 PR 的 base 选 main，上游同步使用 git merge origin/main。

切换不会删除旧分支；不需要重置、强推或重新下载镜像。
