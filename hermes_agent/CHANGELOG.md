# Changelog

## 0.10.2

- 修复 Home Assistant WebSocket 反复 502 的问题（`ws://supervisor/core/api/websocket` → `/core/websocket`）
  - 上游 v0.10.0 在 `gateway/platforms/homeassistant.py` 写死了 `/api/websocket` 后缀，但 HA Supervisor 代理的 WS 端点在 `/core/websocket`，没有 `/api` 段
  - 新增 `hermes_agent/patches/ha_ws_url.py`，在镜像构建时对上游模块打条件补丁：URL 含 `supervisor` 时走 `/websocket`，其他场景保留原逻辑
- 清掉上游 v0.10.0 对 `MESSAGING_CWD` 的 deprecation warning
  - run.sh 不再把 `MESSAGING_CWD` 写进 `.env`，改写到 `${HERMES_HOME}/.addon-runtime`（只给 ttyd 用）
  - `terminal.cwd` 已通过 `config.yaml` 配置（上游推荐方式）
  - 主动 `pop` 老 `.env` 里的 `MESSAGING_CWD=...` 残留

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
