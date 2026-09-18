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


## [2026-09-19T06:24:51.440963] feat: 新增 Open WebUI Home Assistant 官方加载项 (Add-on)
- **执行 Agent**：Hermes Agent
- **操作目标**：在仓库 `sunboss/hermes-agent-ha-addon` 新增开箱即用的 `open_webui` 插件
- **核心功能**：
  1. 支持 Home Assistant 原生 Ingress（嵌入 HA 侧边栏，安全便捷）与宿主机独立端口 `8080/tcp`
  2. 对话历史、配置与模型数据完整持久化存储于 `/config/open-webui`
  3. 支持动态连接外部 OpenAI API 或本地 Ollama 实例
- **验证证据**：远端 HEAD 推进至 `af34436eb4`，GitHub Actions CI 流水线 (Run ID: 35401379124) **全绿通过 (success)**
- **关联归档**：`ops/history/20260919_062451_add_open_webui.json`
- **回滚点**：`git reset --hard e396fd10821b066cf8dfddb8f58b09f4dd715db1`


## [2026-09-19T06:35:56.421300] feat: 开放 Hermes API 8642 端口并预设 Open WebUI 内部直连
- **执行 Agent**：Hermes Agent
- **操作目标**：打通 HAOS 内部 `open_webui` 与 `hermes_agent` 两个插件的无缝互联
- **核心变更**：
  1. `hermes_agent/config.yaml`：开放 `8642/tcp: 8642` 端口映射
  2. `hermes_agent/scripts/configure.py`：将 `API_SERVER_HOST` 从 `127.0.0.1` 调整为 `0.0.0.0`，允许跨容器与局域网调用
  3. `open_webui/config.yaml`：默认 `openai_api_base_url` 直接预设为 `http://hermes_agent:8642/v1`，实现开箱即用直接互通
- **验证证据**：远端 HEAD 推进至 `ea2c064723`，GitHub Actions CI (Run ID: 35402183644) **通过 (success)**
- **关联归档**：`ops/history/20260919_063556_expose_api_port_8642.json`
- **回滚点**：`git reset --hard 33b32cb5e4e8992ad34e2c34614ff797bebe5521`
