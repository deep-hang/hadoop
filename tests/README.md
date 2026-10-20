# 验证入口

## 组员：验证已导入的环境

按 [使用说明第 7 步](../docs/platform-setup.md) 运行 verify。它检查 Java、javac、Hadoop 版本，并编译运行 Hadoop API 探针；不验收成员模块。

## 维护者：检查公共文件

在项目根目录执行，Windows 的 Bash 命令可在 Git Bash 中运行：

```text
python tests/check-contract.py
bash -n docker/entrypoint.sh
bash -n scripts/dev.sh
bash -n tests/verify-base.sh
bash -n tests/verify-entrypoint.sh
bash tests/verify-entrypoint.sh
```

Python 检查仅需标准库，覆盖公共契约、目录、XML、换行与文档链接。入口测试覆盖缺少工具/配置、参数和退出码。

公共运行环境变更后还需按 [镜像维护说明](../docker/README.md) 构建并运行 verify。退出码非零即失败，静态检查不能替代实际容器验证。
