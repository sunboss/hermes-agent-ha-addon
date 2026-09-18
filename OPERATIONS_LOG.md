# Operations Log


## [2026-09-19T05:02:34.903626] feat: 升级 Hermes 上游基底至 v2026.9.14 并适配 HAOS 最新架构
- **执行 Agent**：Hermes Agent
- **操作目标**：升级 `sunboss/hermes-agent-ha-addon` 至 `2026.9.18.0` 并优化适配 Home Assistant OS 最新插件结构
- **核心变更**：
  1. `Dockerfile` / `config.yaml` / `CHANGELOG.md` 升级为 `2026.9.18.0`，基底采用官方当前最新稳定镜像 `nousresearch/hermes-agent:v2026.9.14`
  2. `patches/ha_ws_url.py` 全面重构，适配官方插件化目录结构（`plugins/platforms/homeassistant/adapter.py`），修复 Supervisor WebSocket 代理 502 隐患
- **验证证据**：远端 HEAD 已推进至 `491ba0db70`，经 GitHub API 验证成功
- **关联归档**：`ops/history/20260919_050234_upgrade_haos_addon.json`
- **回滚点**：`git reset --hard 13765239ed778330ca0489aa597a7eb8df01e858`
