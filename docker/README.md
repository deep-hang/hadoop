# 基础镜像维护（组长使用）

组员按 [使用说明](../docs/platform-setup.md) 下载并导入镜像，不需要自行构建。

组长修改公共镜像后，在项目根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 build
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 verify
```

Mac 对应执行 bash scripts/dev.sh build、bash scripts/dev.sh verify。

版本和校验值固定在 Dockerfile 中。默认从 Apache Archive 下载 Hadoop；下载慢时可将同一官方 hadoop-3.3.6.tar.gz 放入 docker/cache/ 再构建，两条路径均检查固定 SHA512。缓存不提交 Git，也不保留在运行镜像内。

发布新镜像前记录版本、镜像 ID 与验证结果，按 [协作规则](../docs/contributing.md) 更新分发文件。
