# Changelog

## 0.10.1

- 统一 add-on 版本号到 `0.10.1`
- 保持上游 Hermes 固定在 `v2026.4.16`
- 保留新的 Home Assistant `config` 持久化目录布局
- 修正仓库首页与版本展示信息

## 0.10.0

- 升级上游 Hermes 到 `v2026.4.16`
- `Dockerfile` 和 `build.yaml` 统一改为 digest 固定
- add-on 存储布局切到 `/config/addons_data/hermes-agent/...`
- `run.sh` 改成新的 Home Assistant 持久化目录方案
- 启动页、终端页、`app.js`、`server.py` 一并更新
