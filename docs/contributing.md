# 小组协作规则

1. 群昵称改为“姓名 + 任务号”，例如“周建行 1”。
2. 从 common/phase0-bootstrap 创建自己的功能分支，命令见 [使用说明](platform-setup.md#task-branch)。当前没有 main，PR 目标为 common/phase0-bootstrap。
3. 每人修改自己的目录；公共配置、镜像、脚本和跨模块变更先由组长协调。
4. 一次提交一个可验证功能。提交说明用“类型(模块): 具体内容”；公共变更新建 .changes/日期-任务号-主题.md，写原因、影响、验证和回滚方式，不把所有人的变更都追加到同一个文件。
5. 自己开发、自己测试；完成后推送自己的分支，向 common/phase0-bootstrap 提交 PR，不直接推送 main 或公共底座分支。
6. PR 写明改动、接口变化、执行过的测试与结果。测试未通过时保留草稿，组长审核后合并。
7. 每人提交本模块实验说明、PPT、含字幕配音的视频和讲解，交接要求见 [联调说明](member-onboarding.md)。

## 公共版本管理

当前镜像以 phase0-image-v0.1 预发布分发；main 和 v0.1-bootstrap 稳定标签由组长后续确定。升级公共环境需使用新镜像标签，记录镜像 ID。

需要回退时，在修复分支使用 git revert 回退具体提交并提 PR，不强推、不重写 main；代码、配置和镜像版本一起恢复。

## 文件放置

- 测试按 [tests/ 分工](../tests/README.md) 放入自己的子目录；实验材料按 [docs/modules/ 分工](modules/README.md) 存放。
- compose/bootstrap.yaml 属于 1 号；2 号新建独立集群文件。config/common/、config/hdfs/、config/yarn/ 分别由 1、3、4 号维护，不混写配置。
- apps/ 和 modes/ 已按模块分开，代码和运行入口仍放原目录；scripts/ 保留公共工具，模块专用脚本放自己的功能目录。

## PR 是什么、怎么提交

PR（Pull Request）就是“申请把自己的分支改动合并到公共分支”，提交 PR 不等于已经合并。

1. 在电脑终端、项目根目录提交并推送自己的功能分支；先用 git status 核对只包含自己负责的文件。
2. 打开 GitHub 仓库的 Pull requests，点击 New pull request。
3. base 选择 common/phase0-bootstrap，compare 选择自己的 feat/... 分支；在文件列表中核对改动范围。
4. 点击 Create pull request，写清做了什么、如何运行、测试结果和未完成项，等待组长审核。
5. 根据反馈在原功能分支修改并推送，原 PR 会自动更新；新增改动后需要重新审核。

## 组长怎么审核

1. 打开 PR 的 Files changed，确认没有误改公共文件或他人目录，再按交接命令复验。
2. 有问题时提出修改意见；通过后用 Review changes → Approve → Submit review 批准。
3. 确认改动和测试无误，再用 Merge pull request 合并。PR 审批通过本身不等于自动合并。

公共分支启用 PR 审核和代码所有者审核；.github/CODEOWNERS 指定 @deep-hang 为所有文件的审核人。组员不能直接推送公共分支，修改必须经组长批准；新改动会使旧批准失效。禁止普通成员强制推送或删除公共分支。

仓库所有者保留管理员维护权限；自己的维护变更不能由本人给自己的 PR 审批，必要时可使用所有者维护权限。目录归属仍按模块约定执行，这些规则保护的是合入公共分支的过程。
