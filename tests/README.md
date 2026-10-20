# 验证入口

## 无 Docker 的静态 / 入口验证

```text
python tests/check-contract.py
bash -n docker/entrypoint.sh
bash -n scripts/dev.sh
bash -n tests/verify-base.sh
bash -n tests/verify-entrypoint.sh
bash tests/verify-entrypoint.sh
```

Windows 可用 Git Bash 执行 Bash 检查。`check-contract.py` 仅需 Python 标准库，检查契约一致性、版本锁定、目录、XML、换行与文档链接；不在容器运行时依赖 Python。

## Compose 与容器验证

完整命令见根 README。先 `config`，再 `build`，最后 `verify`。`verify-base.sh` 检查真实工具版本并用 Hadoop 类路径编译、运行一个配置加载探针；不运行成员模块。

退出码非零即失败。运行验证待补时，不可用静态检查结果替代容器成功记录。
