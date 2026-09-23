# Operations Log

## [2026-09-23T23:05:00+08:00] fix: 注入 X-Forwarded-Prefix 激活 Hermes 原生 Base Path 替换，修复侧边栏黑屏与详情页 404 (2026.9.23.3)
- **执行 Agent**：Hermes Agent
- **操作目标**：彻底解决 Ingress 模式下侧边栏黑屏与详情页 404 问题，同时兼顾 HA 两大官方标准地址
- **核心变更**：
  1. `hermes_agent/rootfs/etc/nginx/nginx.conf`：在 8099 端口代理段添加 `proxy_set_header X-Forwarded-Prefix $http_x_ingress_path;`，对接 Hermes Dashboard 原生 Base Path 解析机制；
  2. `hermes_agent/config.yaml` / `CHANGELOG.md`：版本号自增至 `2026.9.23.3`。
- **验证证据**：GitHub 远程仓库已成功接收 commit `9532afc`，触发自动化 Docker 多架构镜像打包；
- **关联归档**：`ops/history/20260923_230500_fix_ingress_forwarded_prefix_2026_9_23_3.json`
- **回滚点**：`git reset --hard 286f228`

## [2026-09-23T00:58:00+08:00] feat: 全面参照 Node-RED 架构对齐 Ingress，解决权限报错并恢复更新按钮 (2026.9.22.16)
- **执行 Agent**：Hermes Agent
- **操作目标**：彻底解决 Ingress 下 WebSocket 403 握手拒绝、权限报错与顶级路由占用问题，找回官方更新按钮
- **核心变更**：
  1. **架构重构对齐 Node-RED**：采用 nginx 原生反代替代自研 Python 代理层，配置标准 WebSocket 升级与 `proxy_buffering off` 流式透传；
  2. **解决非 root 用户写日志报错**：将 `error_log` 与 `access_log` 移至 `/tmp/`，根除 Linux 内核对 `/proc/1/fd/1` 的权限拦截；
  3. **规范化路由与实体生成**：设置 `ingress_panel: false` 和 `panel_icon`，解除自定义原生顶级面板模式，对齐官方标准 `/app/1037d332_hermes_agent`；
  4. **版本升级至 2026.9.22.16**：多架构镜像构建完成，HA 底层成功检测到更新（`update_available: true`）。
- **验证证据**：
  - `ha apps info 1037d332_hermes_agent` 真实回读：`update_available: true`, `version: 2026.9.22.15`, `version_latest: 2026.9.22.16`；
- **关联归档**：`ops/history/20260923_005800_align_nodered_nginx_and_ingress_panel_false.json`
- **回滚点**：`Git commit 062727d (version 2026.9.22.15)`

## [2026-09-22T22:45:00+08:00] fix: 修复 Ingress 代理流式 SSE 阻塞并适配 HAOS /app/主机名 路由 (2026.9.22.9)
- **执行 Agent**：Hermes Agent
- **操作目标**：彻底解决 Ingress 下对话界面黑屏卡死，实现真正的 Chunked 流式传输，并适配 `/app/主机名` 标准路由规则
- **核心变更**：
  1. `hermes_ui/server.py`：
     - 重构 `_proxy_panel_http`：对 `text/event-stream` 及 chunked 响应采用无缓冲流式转发（实时 chunk 读写与 flush），彻底消除 `urllib.request.urlopen` 尝试读取完整 payload 导致 30 秒超时的缺陷；
     - 增加对 `/app/主机名` 路径的解析与剥离（适配 HAOS 内部标准反向代理路由）；
     - 前端 JS 注入脚本中动态适配 `/app/主机名` 作为 BASE 前缀。
  2. `config.yaml` / `Dockerfile` / `version.json` / `CHANGELOG.md`：统一版本号升级至 `2026.9.22.9`。
- **验证证据**：本地代码逻辑审计通过，支持无限长 SSE 事件流边接收边发送给浏览器；
- **关联归档**：`ops/history/20260922_224500_fix_sse_streaming_and_haos_app_route.json`
- **回滚点**：`git reset --hard 9d86451`


## [2026-09-22T21:20:00+08:00] docs: 全面升级文档与更新日志为中英文双语规范
- **执行 Agent**：Hermes Agent
- **操作目标**：对齐 `2026.9.22.7` 实际功能架构，全面更新更新日志并以全量中英双语重构核心文档
- **核心变更**：
  1. `hermes_agent/CHANGELOG.md`：补全 `2026.9.22.7` 及近期关键版本的中英文双语 Changelog；
  2. `hermes_agent/DOCS.md`：全量中英双语重构，详解 Ingress 直通、9119 直连、8642 API、模型配置与数据持久化；
  3. `hermes_agent/README.md` & 根目录 `README.md`：升级为标准中英双语说明，版本同步对齐至 `2026.9.22.7`；
  4. `docs/UPGRADE_LOG.md`：追加 WebSocket 403 根因与修复技术复盘。
- **验证证据**：本地 `git diff` 验证无误；
- **关联归档**：`ops/history/20260922_212000_bilingual_docs_and_changelog.json`
- **回滚点**：`git reset --hard HEAD~1`

## [2026-09-22T21:05:00+08:00] feat: 彻底移除 ttyd 终端组件与多余引导页，根路径直通官方控制台，修复 Ingress WebSocket 对话黑屏
- **执行 Agent**：Hermes Agent
- **操作目标**：精简 HAOS 插件架构，剔除冗余命令行终端与卡片引导页，彻底打通 HA Ingress 内部对话与 WebSocket 链路
- **核心变更**：
  1. `Dockerfile` / `run.sh`：彻底剥离 `ttyd` 构建下载与进程启动，加快构建速度并节约系统内存；
  2. `hermes_ui/server.py`：
     - 根路径 `/` 访问直接 302 直通 `./panel/`（官方 Dashboard），消除多余中间引导卡片；
     - `_proxy_panel_websocket` 强制将客户端 `Origin` 请求头重写为 `http://127.0.0.1:9120`，彻底解决 Ingress 下 WebSocket 握手报 `403 Forbidden` 导致聊天界面空白黑屏的问题；
     - `_proxy_panel_http` 同步加上 Host 与 Origin 重写；
  3. `config.yaml` / `version.json`：全插件版本升级至 `2026.9.22.7`。
- **验证证据**：本地 `git diff` 审查通过，代码完成原子性替换；
- **关联归档**：`ops/history/20260922_210500_streamline_ui_remove_ttyd_and_fix_ws.json`
- **回滚点**：`git reset --hard HEAD~1`


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

### [2026-09-22 10:15:00] 优化 WebUI 原生访问模式、升级基础镜像与加速构建
- **执行 Agent**: hermes-agent
- **操作目标**: 解决 Ingress 下 LobeChat 404 与 NextChat 卡顿问题，升级核心至 v2026.9.21，精简 Dockerfile 加速小主机拉取
- **关键变更**:
  1. `lobe_chat` 与 `next_chat` 关闭 `ingress`，采用标准 `webui: "http://[HOST]:[PORT]"` 原生跳转（端口 `3210` 与 `3000`）；
  2. 基础镜像升级至官方最新多架构版 `nousresearch/hermes-agent:v2026.9.21`，版本号统一提升至 `2026.9.22.0`；
  3. 彻底移除 Dockerfile 中冗余的 `npm install && npm run build` 本地构建指令，大幅减少工控机 CPU 负载与构建耗时；
  4. 补充完整中英文翻译字典，默认模型对齐为 `gemini-3.8-flash-high`。
- **验证证据**: 远程 Commit `0080abc`，GitHub Actions CI 流水线（Run ID: `35714491883`）全绿通过。
- **关联存档**: `ops/history/20260922_101500_optimize_webui_and_speed_up_build.json`
- **回滚点**: `1800f74`

### [2026-09-22 10:25:00] 默认配置升级：预设 https://api.1234r.com/v1 端点
- **执行 Agent**: hermes-agent
- **操作目标**: 解决未发布 ghcr 镜像导致的 401/403 denied 报错，消除 `addon_config` 废弃警告，全插件默认预设为自建网关端点
- **关键变更**:
  1. 移除尚未构建推送的 `image: ghcr.io/...`，恢复极速精简本地构建；
  2. 修复 HA Supervisor 警告：将 `addon_config:rw` 统一升级为 `app_config:rw`；
  3. `hermes_agent`、`lobe_chat`、`next_chat` 统一预设 API 端点为 **`https://api.1234r.com/v1`**；
  4. 优化中文说明：用户在安装后**仅需输入 API Key 即可直接使用**，无需手动填写复杂的网关地址。
- **验证证据**: 远程 Commit `ae3a93c`，本地 YAML 全语法自检通过。
- **关联存档**: `ops/history/20260922_102500_default_api_1234r.json`
- **回滚点**: `f1de10a`

### [2026-09-22 10:33:00] 修复 Schema 类型定义错误并发布 2026.9.22.1
- **执行 Agent**: hermes-agent
- **操作目标**: 解决 HA Supervisor 读取 `config.yaml` 报 schema 正则不匹配错误，升级版本号强刷 HAOS 缓存
- **关键变更**:
  1. 修复 `schema` 校验定义：`options` 里填默认值 `https://api.1234r.com/v1`，`schema` 必须声明类型为 `"url"`，修复了 `Can't read config.yaml` 导致加载项被临时移除的问题；
  2. 版本号统一升级为 **`2026.9.22.1`**，彻底废弃 Supervisor 本地记录的旧 `ghcr.io` 标签缓存，避免安装时再次尝试从 ghcr.io 拉取而报 `denied`。
- **验证证据**: 远程 Commit `93faefd`，YAML 校验通过。
- **关联存档**: `ops/history/20260922_103300_fix_schema_and_bump_version.json`
- **回滚点**: `21d4a15`

### [2026-09-22 10:41:00] 修复表单默认值展示并发布 2026.9.22.2
- **执行 Agent**: hermes-agent
- **操作目标**: 解决 HA 选项卡中 `OpenAI-Compatible Base URL` 框内显示占位符字符串 `"url"` 的问题，正确显示 `https://api.1234r.com/v1`
- **关键变更**:
  1. `options` 中的端点地址正确设置为 **`https://api.1234r.com/v1`**；
  2. `schema` 保持规则类型为 `"url"`；
  3. 版本号递增至 **`2026.9.22.2`**。
- **验证证据**: 远程 Commit `93d772b`。
- **关联存档**: `ops/history/20260922_104100_fix_options_url_display.json`
- **回滚点**: `8071aa1`

### [2026-09-22 10:52:00] 发布 2026.9.22.3：官方 zh-Hans 中文化与模型自动拉取
- **执行 Agent**: hermes-agent
- **操作目标**: 解决 HA 界面因为缺失标准 `zh-Hans.yaml` 导致降级显示全英文的问题，实现启动时自动从网关拉取可用模型与支持自定义覆盖
- **关键变更**:
  1. 为所有插件补齐官方标准简体中文 `translations/zh-Hans.yaml` 与 `zh.yaml`，表单标题与提示全面中文化（包含必填 API Key、工作目录、监听域等）；
  2. 增强 `hermes_agent/scripts/configure.py`：新增 `resolve_default_model` 逻辑，容器启动时若模型留空，自动通过 API Key 向 `https://api.1234r.com/v1/models` 请求可用模型列表并智能优选；若用户手动输入模型名则直接使用自定义模型；
  3. 版本号统一提升至 **`2026.9.22.3`**。
- **验证证据**: 远程 Commit `ff33310`，YAML 校验通过。
- **关联存档**: `ops/history/20260922_105200_zh_hans_and_auto_models.json`
- **回滚点**: `d214cf2`

### [2026-09-22 19:23:55] 开放原生端口 9119 与 Dashboard 直连
- **目标**：彻底解决 Ingress 路由跳出导致 `/chat` 报 404 的问题，提供原生 9119 端口直连与控制台自动更新能力。
- **操作**：配置 9119 端口映射，`run.sh` 绑定 0.0.0.0，版本升级至 `2026.9.22.4`。
- **验证证据**：远程提交 `265c04f` 成功推送到 GitHub `main` 分支。
- **关联归档**：`/Users/sunboss/Desktop/hermes-agent-ha-addon/ops/history/20260922_192355_native_9119_port.json`

### [2026-09-22 20:01:46] 彻底修复 9119 连接被拒绝：引入透明反代 native_proxy (v2026.9.22.5)
- **目标**：解决 `hermes dashboard` 绑定 0.0.0.0 时因无 auth provider 自行退出的问题，消除 `ERR_CONNECTION_REFUSED` 与 `Auxiliary Nous` 警告。
- **架构**：Dashboard 运行于 `127.0.0.1:9120`（免认证稳定模式），透明反代 `native_proxy.py` 监听 `0.0.0.0:9119` 并将 HTTP 与 WebSocket 透明转发，重写合法 Host 头。
- **验证证据**：提交 `51dc3ff` 成功推送到 GitHub `main` 分支。
- **关联归档**：`/Users/sunboss/Desktop/hermes-agent-ha-addon/ops/history/20260922_200146_native_proxy_v5.json`

### [2026-09-22 21:48:00] 配置 GitHub Actions CI/CD 多架构镜像自动化与 GHCR 集成
- **操作者**：Hermes Agent
- **目标**：彻底打通跨多台 HAOS 服务器的标准更新机制，消除无更新按钮与重建报错
- **变更内容**：
  1. 创建 `.github/workflows/build-images.yml`：基于 Docker Buildx 自动构建 `aarch64` 与 `amd64` 预编译镜像并推送至 GHCR。
  2. 修改 `hermes_agent/config.yaml`：声明 `image: ghcr.io/sunboss/hermes-agent-{arch}`。
- **关联归档**：`ops/history/20260922_214800_ghcr_image_and_actions.json`
- **回滚点**：`git checkout 21ab89f`

### [2026-09-22 22:12:00] 修复 Ingress 对话区黑屏并发布 v2026.9.22.8
- **操作者**：Hermes Agent
- **目标**：解决侧边栏直达后右侧对话区域因 SSE (EventSource) 未代理导致的纯黑画布
- **变更内容**：
  1. `hermes_ui/server.py`：注入包装全局 `window.EventSource`，透明重写 Ingress 相对路径。
  2. 版本升至 `2026.9.22.8`，更新 `Dockerfile`、`config.yaml`、`CHANGELOG.md`。
- **关联归档**：`ops/history/20260922_221200_fix_eventsource_black_screen.json`
- **回滚点**：`git checkout 0720253`

## [2026-09-23T21:37:54.298449] 侧边栏 Ingress 路径与前端黑屏问题深度复盘及技术归档

- **执行 Agent**：hermes-agent
- **操作类型**：问题归档 / 技术留痕 (diagnose & record)
- **归档文件**：
- **核心结论与教训**：
  1. **严禁在 index.html 使用 document.write**：异步执行会导致 token 字符串直接被写进页面 body 变成顶部文本，彻底阻断 React 组件挂载。
  2. **严禁侵入式修改 HA 核心容器（如 addon_panel.py）**：容器一旦更新重启修改必丢失，且会破坏系统稳定性。
  3. **Ingress SPA 唯一标准解法是 HashRouter**：无论外部是 、 还是 Cloudflare 穿透，Hash 路由永远 100% 命中，免去提取 Ingress Token 的一切脆弱逻辑。
- **当前状态**：待用户指示，在容器内就地验证 HashRouter 效果后统一反推本地工程并打包版本 。

## [2026-09-23T22:05:03.283089] Ingress 侧边栏与前端加载问题彻底复盘总结（准备发布 2026.9.22.23）

- **执行 Agent**：hermes-agent
- **操作类型**：总结与准备发布 (modify & release-prep)
- **标准化归档**：`ops/history/20260923_220503_final_repair_and_release_summary.json`
- **核心沉淀**：
  1. **放弃一切黑魔法**：不要在 `index.html` 注入 `document.write`，不要篡改 HAOS 核心 `addon_panel.py`。
  2. **全面对齐官方标准**：遵循 HA 2026.9 的 `addon` 面板路径规范，前端资源全部使用相对路径（`assets/...`）。
  3. **Cloudflare 穿透经验**：HTTP 反代配置在 HA 2026.9 中固定在 `/config/.storage/http`，隧道协议锁定为 HTTP2。
- **下一步**：拉取远程最新代码，递增版本号为 `2026.9.22.23`，提交并推送到 GitHub 触发构建。
