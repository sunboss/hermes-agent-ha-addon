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


## [2026-09-19T07:31:18.961994] feat: 替换 open_webui，新增 LobeChat 与 NextChat 专属加载项
- **执行 Agent**：Hermes Agent
- **操作目标**：移除 `open_webui` 插件，新增更现代易用的 `lobe_chat` (LobeChat) 与轻量快速的 `next_chat` (NextChat) 插件
- **核心特性**：
  1. **LobeChat**：多模态、插件市场、TTS 语音支持，HA Ingress 侧边栏无缝嵌入，默认直连 `http://hermes_agent:8642/v1`
  2. **NextChat**：极简超轻量，毫秒级响应，HA Ingress 侧边栏无缝嵌入，默认直连 `http://hermes_agent:8642/v1`
- **验证证据**：远端 HEAD 推进至 `6af118494f`，GitHub Actions CI 流水线 (Run ID: 35405932738) **全绿通过 (success)**
- **关联归档**：`ops/history/20260919_073118_replace_webui_with_lobe_and_nextchat.json`
- **回滚点**：`git reset --hard b01ca19a05df82c9f518a385208f2d529815c46e`


## [2026-09-19T07:46:56.761474] fix: 修复 LobeChat 与 NextChat 官方原版图标及 Docker 构建失败问题
- **执行 Agent**：Hermes Agent
- **操作目标**：
  1. 替换原有的占位符图标为原版官方高清图标（解决 HA 商店中图标重复退化为“H”的问题）
  2. 修复 HAOS 安装时 Docker 构建报错 `apk: not found` / `apt-get: not found`（代码 127）
- **核心修复**：
  1. **原版高清图标更新**：下载并替换了 LobeChat（460x460 RGBA）和 NextChat（512x512 RGBA）的原版官方品牌 Logo 与触摸图标
  2. **容器启动器零依赖化**：LobeChat 与 NextChat 官方镜像基于 Distroless 极简 Node 镜像（无 apk/apt/bash 包管理器）。已全面改用纯 Node.js 编写的 `entrypoint.js`，无须调用 apt/apk，彻底根治构建报错
  3. 版本号提升至 `2026.9.18.1`
- **验证证据**：远端 HEAD 推进至 `5e23590244`，GitHub Actions CI (Run ID: 35406956227) **全绿通过 (success)**
- **关联归档**：`ops/history/20260919_074656_fix_icons_and_docker_build.json`
- **回滚点**：`git reset --hard 1d6fa90beff99cba4cae096417fae7870933fa12`
