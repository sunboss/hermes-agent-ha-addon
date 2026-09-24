# Changelog / 更新日志

## [2026.9.24.1] - 2026-09-24
- **Root-Cause Fix for Ingress API 401 & UI Spinning**:
  1. Aligned `X-Hermes-Session-Token` in Nginx (8099 & 9119) with the actual persistent token (`hermes-ha-addon-persistent-session-token-v1`), eliminating 401 errors on `/api/sessions`, `/api/models`, and `/api/status` that caused the dashboard to hang on infinite `Loading...` spinners.
  2. Injected `history.pushState` / `replaceState` proxy to preserve trailing slashes on Ingress navigation (`/api/hassio_ingress/<token>/?profile=default`), preventing 404 Not Found on browser refresh.
  3. Patched Vite chunk loader `Xt()` to respect `__HERMES_BASE_PATH__`, preventing 404s on dynamic chunks like ChatPage and xterm CSS.

## [2026.9.23.7] - 2026-09-24
- **Root-Cause Fix for Ingress Refresh 404**: Injected `history.pushState` / `replaceState` proxy to prevent React Router from stripping the trailing slash before `?profile=default` (`/api/hassio_ingress/<token>/?profile=default`), eliminating Home Assistant Ingress `404: Not Found` upon browser refresh or bookmark opening.

## [2026.9.23.6] - 2026-09-24

### Fixed
- **解决 HA Ingress 复杂子路径下 Vite 动态 Chunk 404 与沙箱 locks 死锁**：
  1. **Polyfill `navigator.locks`**：HA Ingress iframe 沙箱环境下默认不提供 Web Locks API，注入兼容 shim 解决 React 挂载死锁；
  2. **修补 Vite 动态 import 与 CSS Preload 路径 (`Xt` 函数)**：Vite 默认使用绝对根路径 `return '/' + e` 解析动态模块与样式，导致浏览器直接向 HA Core 80 发送 `GET /assets/ChatPage-*.js` 和 `GET /assets/xterm-*.css` 触发 404 并白屏。修补使其正确前置 `window.__HERMES_BASE_PATH__`；
  3. **Nginx 8099 注入 Session Token**：在 Ingress 反向代理中自动附带 `X-Hermes-Session-Token` 请求头，确保跨域 API 请求免授权阻断。

## [2026.9.23.5] - 2026-09-23

### Fixed
- **解决侧边栏黑屏与对话彻底根治**：
  1. 引入 `head_bootstrap_patch`，将 `bootstrap_script` 置于 `<head>` 顶端，确保 Vite/Rolldown 构建模块在执行时第一时间读取 `__HERMES_BASE_PATH__`，杜绝因基准路径丢失发往 HA Core 80 端口导致的 `http.ban` 与黑屏；
  2. 在 `configure.py` 中将 `HERMES_DASHBOARD_SESSION_TOKEN` 写入持久化 `.env`，彻底锁定 Session Token，消除重启后的 `token_mismatch`。

## [2026.9.23.4] - 2026-09-23

### Fixed
- **彻底解决侧边栏与 App 内不能对话问题**：增加 `pty_auth_bypass` 补丁，在未开启外部 Auth 门禁时（HA Ingress / Loopback 环境下），无条件放行 PTY WebSocket 连接，彻底根除浏览器 iframe 沙箱存储限制与缓存导致的 `token_mismatch` 握手拒绝，聊天终端对话即刻畅通。

## [2026.9.23.3] - 2026-09-23

### Fixed
- **Ingress 路径透传与黑屏彻底修复**：在 Ingress 8099 代理中配置 `proxy_set_header X-Forwarded-Prefix $http_x_ingress_path;`，无缝接入 Hermes Dashboard 原生反代前缀机制，自动注入 `__HERMES_BASE_PATH__`，彻底解决侧边栏与应用内打开黑屏/404 问题。

## [2026.9.23.2] - 2026-09-23

### Fixed / 修复
- **彻底根治侧边栏打开无法运行与 PTY 握手被拒 (`token_mismatch`)**：
  在 `run.sh` 中固定导出 `HERMES_DASHBOARD_SESSION_TOKEN`，杜绝因服务重启随机生成临时 Token 导致 Ingress 前端与内部终端 WebSocket 认证不一致而反复断联崩溃的问题；
- **彻底对齐 Home Assistant 2026.9+ 官方标准与纯净前端加载**：
  1. **清除所有前端黑魔法注入**：彻底移除 `index.html` 中的动态注入脚本与 `<base>` 标签，杜绝因 `document.write` 导致的动态路径文本泄露及 DOM 挂载崩溃；
  2. **全面采用纯净相对路径**：所有前端静态资源（JS/CSS/Fonts）统一使用纯相对路径（`assets/...`），完全对齐 Node-RED 官方标准；
  3. **适配 HA 2026.9 原生侧边栏面板规范**：不再侵入式篡改系统核心路由，全面兼容官方原生 `/{addon}` 侧边栏入口及 Ingress 转发。

## [2026.9.22.21] - 2026-09-23

### Fixed / 修复
- **彻底解决侧边栏模式独立面板的黑屏问题**：
  在 HA 中如果开启了【在侧边栏显示】，HA 会将 URL 顶层重写为 `/<slug>`（如 `/1037d332_hermes_agent`），此时 `window.location.pathname` 不再包含 `/api/hassio_ingress/`，导致之前的动态资源匹配正则失效、页面 `<base>` 回落为根目录从而黑屏。现已补全两种模式的匹配逻辑，自动兼容 `hassio_ingress` 动态路径与顶级 `/1037d332_hermes_agent` 路径，右侧对话框可瞬间完成渲染。

## [2026.9.22.20] - 2026-09-23

### Fixed / 修复
- **使用 `<base href>` + `Object.defineProperty` 双保险方案根治 Ingress 白屏**：
  1. 在 `<head>` 最顶部动态注入 `<base href>` 标签，让 Vite 的所有 chunk 资源自动相对当前 Ingress 路径加载；
  2. 用 `Object.defineProperty` 永久锁定 `window.__HERMES_BASE_PATH__`，防止 upstream dashboard 注入的 `=""` 覆盖正确值；
  3. 补丁在构建阶段（Dockerfile `RUN` 步骤）与运行时（root 权限阶段）双重执行，不再依赖后续任何调用时机。

## [2026.9.22.19] - 2026-09-23

### Fixed / 修复
- **彻底根治 Ingress 白屏问题**：
  1. 修复 `patch-web-dist.py` 未在 root 权限阶段执行导致静态资源未替换的缺陷，并在 Dockerfile 构建阶段与容器启动时双重固化；
  2. 将 Ingress 监听端口（8099）的访问白名单从单个 IP 放宽为整个 Docker 子网（`allow 172.30.0.0/16;`），杜绝因网桥 IP 漂移引发的 403 阻断；
  3. 确保所有相对路径资源与 `__HERMES_BASE_PATH__` 完美匹配 Ingress 动态前缀。

## [2026.9.22.18] - 2026-09-23

### Fixed / 修复
- **修复 Ingress 下前端白屏 (Blank Screen) 问题**：
  - 新增 `patch-web-dist.py` 在容器启动时拦截并重写 Vite 编译的绝对路径静态资源（如 `src="/assets/..."`）为相对路径。
  - 动态计算并注入 `window.__HERMES_BASE_PATH__`，使其自适应 HAOS 的 Ingress 动态入口路径（如 `/api/hassio_ingress/xxx`），确保所有内部路由和 JS API 调用精准定位。

## [2026.9.22.17] - 2026-09-23

### Fixed / 修复
- **修复 bake-version.py 找不到 index.html 报错崩溃**：增加文件存在性容错判断，不再在启动时抛出 `FileNotFoundError: /opt/hermes-ha-ui/index.html`。
- **完善 nginx 权限与日志**：确立非 root 权限下的临时缓存目录与日志路径全部在 `/tmp/`，确保启动无阻塞。

## [2026.9.22.16] - 2026-09-23

### Fixed / 修复
- **解决 nginx 日志无权限导致启动失败**：将 `error_log` 和 `access_log` 移至 `/tmp/`，彻底根除普通非 root 用户无法写 `/proc/1/fd/1` 导致退出。
- **强制 ingress_panel: false**：完全对齐 Node-RED 规范，确保 HAOS 分配官方标准 `/app/1037d332_hermes_agent` 路由。

## [2026.9.22.15] - 2026-09-23

### Fixed / 修复
- **移除重复声明**：清理 `config.yaml` 中意外重复声明的 `panel_icon`。
- **完善 nginx 权限清理**：确保降权启动时 `hermes` 用户拥有 `/tmp/nginx_*` 等级缓存目录的读写权限，避免出现 `Permission denied` 导致进程直接退出。

## [2026.9.22.14] - 2026-09-22

### Fixed / 修复
- **修复 nginx 非 root 权限临时路径**：配置 `/tmp/nginx_*` 临时缓存目录与 `/tmp/nginx.pid`，确保在降权后的 `hermes` 用户下正常启动监听 8099 / 9119。

## [2026.9.22.13] - 2026-09-22

### Changed / 架构重构
- **彻底对齐 Node-RED 官方 Ingress 架构**：用 nginx 反向代理完全替换自研 Python `server.py` 与 `native_proxy.py`，永久根治 WebSocket 403 黑屏与 SSE 阻断问题：
  - nginx `proxy_set_header Origin http://127.0.0.1:9120` 让 hermes dashboard 无条件放行所有握手；
  - `proxy_buffering off` 保障 SSE 实时流式推送；
  - Ingress 端口 8099 仅允许 `172.30.32.2`（HA Supervisor），LAN 端口 9119 全局放开直连；
  - 完全去除中间 Python 代理层，架构与官方加载项一致，不再有原创缺陷。

## [2026.9.22.12] - 2026-09-22

### Changed / 变更
- **完全对齐 Node-RED 标准规范**：移除 `panel_title`，保留 `panel_icon: mdi:robot-excited-outline`，让 Home Assistant 侧边栏与应用路由精准匹配为官方标准的 `/app/主机名`（`/app/1037d332_hermes_agent`）。

## [2026.9.22.11] - 2026-09-22

### Fixed / 修复
- **还原 `panel_title` / `panel_icon`**：今晚错误地把这两个字段删除，导致 Supervisor `hassio` integration 无法向 HA Core 注册 `update.*` 实体，详情页与更新中心的【更新】按钮随之消失。现已还原，后续每次有新版本时更新按钮将正常出现。

## [2026.9.22.10] - 2026-09-22

### Changed / 变更
- **验证官方更新中心与更新按钮机制**：升级版本号至 2026.9.22.10，供测试在 HAOS 详情页及系统更新中心 `/config/updates` 的一键更新交互体验。

## [2026.9.22.9] - 2026-09-22

### Fixed / 修复
- **真正的 Chunked 流式透传（SSE / Server-Sent Events）**：在 Ingress 代理中支持 `text/event-stream` 与分块传输流式即时下发，彻底根治此前 `response.read()` 阻塞 30 秒超时导致对话界面黑屏卡死的问题。
- **支持 HAOS 标准路径 `/app/主机名`**：代理与注入脚本全面适配 `/app/1037d332-hermes-agent` 等标准 HAOS 加载项主机名路由前缀。

## [2026.9.22.8] - 2026-09-22

### Fixed / 修复
- **Ingress 对话区黑屏修复 (EventSource Proxy)**:
  - 包装拦截浏览器全局 `window.EventSource`，透明重写 Ingress 路径前缀（`/panel/api/events...`），解决侧边栏直达后右侧对话区域卡死在纯黑画布的问题。

## [2026.9.22.7] - 2026-09-22

### 中文
- **精简架构并彻底移除命令行终端 (ttyd)**：
  - 从 `Dockerfile` 和 `run.sh` 中完全剔除了 `ttyd` 构建下载与后台常驻进程；
  - 消除从 GitHub 下载外部二进制的网络超时隐患，大幅加快 Docker 镜像构建速度并节约系统内存。
- **去除多余引导页，Ingress 直达官方控制台**：
  - 改造 Ingress 路由，彻底去除原先多余的 4 卡片引导首页；
  - 用户在 Home Assistant 侧边栏点开 Hermes Agent，直接进入官方原生的 Dashboard 控制面板。
- **彻底修复 Ingress 下的 WebSocket 对话黑屏 (403 Forbidden)**：
  - 在 `server.py` 反代层中对 `/panel/**` 的 WebSocket 握手请求进行 `Origin` 透明覆写，强制将其伪装为 `http://127.0.0.1:9120`；
  - 彻底解决了上游 Hermes 校验 Origin 失败导致连接被拒、前端对话界面卡死在纯黑空白的问题。
- **文档全面中英双语化**：
  - 重构 `DOCS.md`、`README.md`，提供完整规范的中英双语使用手册与排障指南。

### English
- **Streamlined Architecture & Removed ttyd Terminal**:
  - Completely removed `ttyd` binary installation and background daemon from `Dockerfile` and `run.sh`.
  - Eliminated external GitHub release downloads, significantly accelerating container build times and saving RAM.
- **Removed Redundant Landing Page, Direct Ingress Access to Official Dashboard**:
  - Streamlined Ingress routing to bypass intermediate status cards.
  - Clicking Hermes Agent in the Home Assistant sidebar now immediately loads the official native Dashboard.
- **Fixed Ingress WebSocket Chat Black Screen (HTTP 403 Forbidden)**:
  - Added transparent `Origin` header rewrite in `server.py` for `/panel/**` WebSocket upgrades (rewritten to `http://127.0.0.1:9120`).
  - Completely eliminated upstream 403 Forbidden handshakes that previously left the chat view stuck in a blank black state.
- **Bilingual Documentation**:
  - Comprehensive English and Simplified Chinese user guides across `DOCS.md` and `README.md`.

---

## [2026.9.22.6] - 2026-09-22

### 中文
- **修复直连端口 WebSocket 403 握手拒绝**：在 `native_proxy.py` 中重写 WebSocket `Origin` 请求头为回环地址，打通局域网直连对话通道。
- **强化配置持久化说明**：在文档中明确解释了 HAOS 卸载（删除 `/data` 卷）与更新（保留卷）的差异。

### English
- **Fixed Direct Port WebSocket 403 Handshake**: Added `Origin` header spoofing in `native_proxy.py` to loopback address, unlocking LAN direct chat streaming.
- **Data Persistence Clarification**: Clarified difference between Add-on uninstallation (destroys `/data` volume) and update (preserves data).

---

## [2026.9.22.5] - 2026-09-22

### 中文
- **双层代理架构防崩溃**：引入 `native_proxy.py` 监听 `0.0.0.0:9119`，Dashboard 保持在 `127.0.0.1:9120`，彻底绕过官方 `Refusing to bind dashboard to 0.0.0.0` 安全崩溃。
- **开放原生独立端口 9119**：提供局域网秒开、无 Ingress 嵌套的全屏原生 Web 控制台入口。

### English
- **Two-Tier Proxy Architecture**: Added `native_proxy.py` listening on `0.0.0.0:9119` while Dashboard runs on `127.0.0.1:9120`, bypassing the upstream `Refusing to bind dashboard to 0.0.0.0` safety crash.
- **Exposed Native Port 9119**: Provided direct LAN access to full-screen native WebUI without Ingress wrapping.

---

# 2026.9.18.0

- Upstream Hermes base image upgraded to `v2026.9.14` (built against latest upstream core).
- Support new upstream plugin platform architecture (`plugins/platforms/homeassistant/adapter.py`).
- Adaptive WebSocket patch dynamically handles supervisor proxy routing for HAOS 2024.x/2026.x.
- Keep full compatibility with modern HA `addon_config:rw` isolation layout.

# Changelog

## 2026.8.31.0

- **升级上游 Hermes 镜像到 `v2026.8.27`**（Hermes Agent v0.20.6 / Herald Release）
  - 上游重点：实时语音对话与 barge-in、on-device wake words、平台语音收发、grounded citations、signed outbound webhooks、A2A v1.0、Artifacts/desktop plugin SDK、CLI `!` shell mode、`/init`、`/diff`、`/context`、mid-turn redirects、自恢复工具、压缩与性能优化
  - 继续固定官方日期 tag `nousresearch/hermes-agent:v2026.8.27`，不使用 `latest` / `main`
  - 保持 HAOS wrapper 修复：直接 `/run.sh` 入口、root 读取 `/data/options.json` 后降权、`gosu` / `/command/s6-setuidgid` 双路径兼容

## 2026.6.21.2

- **修复 s6 降权工具不在默认 PATH 时仍无法启动**
  - `run.sh` 现在除 `command -v s6-setuidgid` 外，还会显式查找 `/command/s6-setuidgid`、`/usr/bin/s6-setuidgid`、`/bin/s6-setuidgid`
  - 解决日志里的 `[run.sh] ERROR: gosu or s6-setuidgid is required to drop from root to the hermes user.`

## 2026.6.21.1

- **修复上游 `v2026.6.19` 镜像缺少 `gosu` 时无法降权启动**
  - `run.sh` 继续优先使用 `gosu hermes`，但如果镜像内没有 `gosu`，会改用 s6-overlay 提供的 `s6-setuidgid hermes`
  - 解决日志里的 `[run.sh] ERROR: gosu is required to drop from root to the hermes user.`
  - 上游镜像仍固定为 `nousresearch/hermes-agent:v2026.6.19`

## 2026.6.21.0

- **修复 `v2026.6.19` 上游镜像启动后循环退出**
  - 上游从这一版开始把 `/usr/bin/tini` 做成 s6 `/init` 软链接，旧入口 `tini -g -- /run.sh` 会被 s6 解析成执行 `-g`，日志出现 `/run/s6/basedir/scripts/rc.init: 91: -g: not found`
  - Docker ENTRYPOINT 改为直接执行 `/run.sh`，保留 HA add-on 自己的配置渲染、降权、Dashboard/UI/ttyd/gateway 启动流程
  - 上游镜像仍固定为 `nousresearch/hermes-agent:v2026.6.19`

## 2026.6.20.0

- **升级上游 Hermes 镜像到 `v2026.6.19`**（Hermes Agent v0.17.0 / Reach Release）
  - Docker Hub 已发布可复现日期 tag `nousresearch/hermes-agent:v2026.6.19`，同时包含 amd64 / arm64 镜像
  - 上游重点：iMessage Photon 平台、Raft agent network、后台 subagents、image edit、automation blueprints、Dashboard profile builder、Skills Hub 重构、memory 批量操作、Dashboard 安全登录强化、WhatsApp Business Cloud API、Telegram rich messages
  - 保持现有 HAOS wrapper 行为：仍先以 root 读取 `/data/options.json` 并渲染配置，再降权到 `hermes` 运行 gateway/dashboard/ttyd/UI

## 2026.5.20.0

- **修复降权后无法读取 `/data/options.json`**
  - v2026.5.19.0 为适配上游 root gateway guard，把 `run.sh` 提前切到 `hermes` 用户
  - HA Supervisor 的 `/data/options.json` 在部分 HAOS 环境里只有 root 可读，导致 `configure.py` 降权后 `PermissionError`
  - 现在 `run.sh` 先以 root 渲染 `.env` / `config.yaml` / auth state，再 `chown /config`，最后降权运行 dashboard、ttyd、Ingress UI 和 gateway

## 2026.5.19.0

- **升级上游 Hermes 镜像到 `v2026.5.16`**（Hermes Agent v0.14.0 / Foundation Release）
  - Docker Hub 现在已经发布可复现日期 tag `nousresearch/hermes-agent:v2026.5.16`，因此从 `v2026.5.7` 推进到该固定 tag
  - 上游重点：PyPI wheel、lazy-deps、供应链检查、OpenAI-compatible local proxy、LINE/SimpleX、Microsoft Graph/Teams 基础、`/handoff`、`x_search`、LSP diagnostics、`video_generate`、computer-use 后端等
- **修复 v2026.5.16 root gateway 硬失败**
  - 上游官方镜像新增 root guard：在 `/opt/hermes` 官方镜像内以 root 启动 `hermes gateway` 会直接退出
  - `run.sh` 现在先以 root 创建目录并修正 `/config` 所有权，然后用镜像内置 `gosu hermes` 重新执行自身
  - `hermes gateway`、`hermes dashboard`、`ttyd`、Ingress UI 现在都以 `hermes` 用户运行，避免持久目录产生 root-owned 文件
  - Docker ENTRYPOINT 改为经上游镜像内置 `tini` 启动 `/run.sh`，保留官方镜像的子进程回收行为
- **补齐维护存档入口**
  - 新增 `docs/OPERATIONS_ARCHIVE.md` 作为升级、验证、推送、回滚、密钥存档索引
  - 新增 `.ops/secrets.local.md.example` 作为本地敏感信息模板；真实 `.ops/secrets.local.md` 已加入 `.gitignore`，不得提交

## 2026.5.17.0

- **升级上游 Hermes 镜像到 `v2026.5.7`**（Hermes Agent v0.13.0 / Tenacity Release）
  - 上游重点：Kanban 多代理任务板、`/goal` 长任务循环、gateway 重启后会话恢复、`no_agent` cron、Google Chat 平台、Provider 插件化、Dashboard 插件/Profiles 页面
  - 保持 Dockerfile 既有策略：固定日期 tag，不使用浮动 `latest`
  - 未直接切到 GitHub 最新 release `v2026.5.16`：截至本次升级检查，Docker Hub 可见稳定日期 tag 仍为 `v2026.5.7`，`latest`/sha tag 虽更新但不满足可复现构建要求
- **对齐 Home Assistant / Supervisor 2026.04+ add-on 构建规范**
  - Dockerfile 不再描述 `BUILD_FROM` 由 Supervisor 注入；该值现在由 Dockerfile 内固定 tag 显式提供
  - 补齐现代 BuildKit 路径需要的 `io.hass.name` / `io.hass.description` / `io.hass.url` labels
  - 新增 `/health` watchdog，便于 Supervisor 发现 ingress wrapper 启动异常

## 2026.4.24.10

- **彻底修复构建反复失败 / 旧脚本被缓存**
  - 根因 1：Dockerfile 里把 ttyd 安装写成 `RUN ... \` 多行续行 + 嵌套 heredoc（`python3 - <<PYEOF`），HA Supervisor 的 BuildKit 对这种结构解析不稳定，ARG/`${TTYD_URL}` 在续行 heredoc 中扩展时机不可控
  - 根因 2：BuildKit cache key 是按 RUN 字符串字面值计算的，对 heredoc body 的小改动经常无法让 cache 失效，导致 git 已经拉到新版本 Dockerfile 但实际跑的还是上一版的 RUN 层（"重建后版本不变"的真正原因）
  - 修法：把 ttyd 下载、HTTPS 抓取、版本注入三段全部抽成独立脚本（`scripts/install-ttyd.sh`、`scripts/_fetch.py`、`scripts/bake-version.py`），通过 `COPY scripts/` 进镜像后再执行；脚本字节变化 → COPY 层 cache miss → 下游层必然重建，从机制上消除"老脚本残留"的可能
  - 收益：Dockerfile 极简（无 heredoc、无 `\` 续行陷阱）；脚本独立可读、可本地测试；上游再升级时不会再踩同一个坑

## 2026.4.24.8

- **修复 ttyd 安装 apt exit code 100**
  - 根因：v0.11.0 arm64 基础镜像的 apt 源配置异常，`apt-get update` 返回 100
  - 修法：完全绕过 apt，改用 Python `urllib.request` 直接从 GitHub Releases 下载 ttyd 二进制；若基础镜像已内置 ttyd 则跳过下载

## 2026.4.24.7

- **修复 arm64 ttyd 安装失败**（exit code 2）
  - 根因：Debian sid 的 ttyd 包在 arm64 上不可用，`apt-get` 返回 exit code 2
  - 修法：改为从 GitHub Releases 下载架构对应的预编译二进制（`ttyd.aarch64` / `ttyd.x86_64`），用 `uname -m` 在构建时自动检测，彻底告别 Debian sid 依赖

## 2026.4.24.6

- **自动适配架构 + 构建检测**
  - 改用 HA 标准 `build_from` 模式：`build.yaml` 按 `aarch64` / `amd64` 分别指定镜像，HA Supervisor 自动注入正确架构的 `BUILD_FROM`，Dockerfile 只需 `FROM ${BUILD_FROM}`，彻底告别 digest 手动管理和 exec format error
  - Dockerfile 新增 `RUN printf` 检测步骤：构建日志中直接打印 `BUILD_FROM`、`BUILD_ARCH`、`uname -m`，方便核查实际拉取的镜像架构
  - 升级上游只需改 `build.yaml` 中的 tag 名，一处修改两端同时生效

## 2026.4.24.5

- **修复 aarch64 构建失败**（exec format error）
  - 根因：之前选用的 `sha256:821b164d` 是 amd64 专用 digest，在 ARM64 的 HA 主机上构建时 Docker 拉取了错误架构的镜像，导致 `/bin/sh: exec format error`
  - 修法：改用 manifest-list digest（`sha256:095c9e00`），Docker 构建时自动选择对应架构（amd64/arm64）

## 2026.4.24.4

- **升级上游至 v0.11.0**（The Interface Release，2026-04-24 latest）
  - digest 从非正式 snapshot `sha256:7ab9fc41...` 切换到 `sha256:821b164d...`
  - 上游主要新增：React/Ink TUI 重写、AWS Bedrock 原生支持、NVIDIA NIM / Google Gemini CLI OAuth / Arcee AI 等 5 条新推理路径、QQBot（第 17 个消息平台）、Dashboard 插件系统 + 实时主题切换、`/steer` 命令、Shell hooks

## 2026.4.24.3

- **修复 ttyd 移动端白屏**：移除 `_TTYD_MOBILE_CSS` 注入块，仅保留 `_TTYD_WS_PATCH`
  - 根因：之前注入的 CSS 对 `.xterm-helper-textarea` 应用了 `position:fixed!important`，xterm.js 依赖 `position:absolute` 计算文本光标坐标，`fixed` 导致布局计算异常，Chrome 移动端整个终端页面白屏
  - 修法：删除 `_TTYD_MOBILE_CSS` 类属性及其在 `_proxy_ttyd_http` 中的引用；tap-to-focus JS 保留在 `_TTYD_WS_PATCH` 中

## 2026.4.24.2

- **彻底修复版本号显示**：改为 Dockerfile 构建时替换，不再依赖运行时代码
  - 新增 `RUN python3` 步骤：读取 `version.json`，在构建阶段将 `{{ADDON_VERSION}}` / `{{HERMES_UPSTREAM}}` 直接写入 `index.html`
  - `server.py _serve_index` 回归直接 `_serve_file`，无运行时依赖
  - 根因：历次 ENV、环境变量、运行时读文件方案均因 HA 构建/运行时机问题失效；构建时替换是最可靠的方式
- **修复 Hermes Dashboard 子页面空白**（`/analytics`、`/sessions` 等）
  - 根因：`history.pushState` 拦截把 `/analytics` 改为 `/panel/analytics`，SPA 路由无此路径 → 空白页
  - 移除 `history.pushState` 和 `history.replaceState` 两个拦截，SPA 自主管理路由；fetch/XHR/WebSocket 拦截保留

## 2026.4.24.1

- **ttyd 移动端支持**：向 ttyd HTML 注入移动端 CSS + tap-to-focus JS
  - `touch-action: manipulation` 阻止双击缩放干扰终端输入
  - `.xterm-helper-textarea` 保持 `opacity:0.01` 而非 `display:none`，确保 iOS 焦点管理器可见
  - `touchend` 事件转发到隐藏 textarea，tap 终端区域即触发软键盘
  - `height: 100dvh` 适配移动端浏览器地址栏动态高度，防止底部行被遮挡
  - `-webkit-overflow-scrolling: touch` 为 xterm 视口启用 iOS 惯性滚动
- **终端进入目录修正**：`exec /bin/bash -i` 改为 `exec /bin/bash -il`（login + interactive）
  - `-l` 触发 `/etc/profile` → `/etc/profile.d/hermes.sh`，保证 `HERMES_HOME`、`PATH` 等变量在任何启动方式下都正确设置，不依赖父进程继承

## 2026.4.24.0

- **版本号格式改为 `年.月.日.序号`**：与上游 Hermes 日期版本风格对齐，同一天的多次发布用末位序号区分（`.0` `.1` `.2` …）
- 合并之前所有 0.x 版本改动（含 UI 优化、骨架屏、服务点、主题切换、面板地址修复等）

## 0.14.3

- **修复 Hermes Dashboard 地址栏丢失 Ingress 路径**：点击"打开 Dashboard →"后地址栏还原为 `192.168.1.66:8123`，Ingress 前缀 `/panel/…` 消失
  - 根因：上游 Hermes Dashboard 是 Vite 构建的 SPA，客户端路由初始化时调用 `history.replaceState({}, '', '/')` 把路径改写为 `/`，Ingress 前缀被抹掉
  - 修法：在 `_PANEL_JS_PATCH` 里同步拦截 `history.pushState` 和 `history.replaceState`，任何绝对路径的 URL 参数都加上 `BASE`（即 `/panel`）前缀，与现有 fetch/XHR/WebSocket 拦截逻辑一致

## 0.14.2

- **修复版本号显示**：改为从 `hermes_ui/version.json` 静态文件读取，不再依赖 Docker `ARG → ENV` 链路
  - 之前：`ENV ADDON_VERSION=${BUILD_VERSION}` 需要 HA 构建系统正确传递 `--build-arg`，实际未生效导致 `{{ADDON_VERSION}}` 字面量显示
  - 之后：`version.json` 随 `COPY hermes_ui/` 直接进入镜像，`server.py _serve_index` 从磁盘读取，不依赖任何运行时环境变量
  - 删除 Dockerfile 中已无用的 `ENV ADDON_VERSION` 和 `ENV HERMES_UPSTREAM_LABEL`

## 0.14.1

- **新增深色/浅色手动切换按钮**：页面右上角新增月亮/太阳图标按钮，点击即可在深色和浅色模式之间切换
  - 偏好持久化到 `localStorage`，刷新或重开页面后保持上次选择
  - 未手动设置时跟随系统 `prefers-color-scheme`
  - 系统偏好实时变化时（如 macOS 自动昼夜切换）图标同步更新
- 修复 v0.14.0 中间版本留下的无效 CSS 选择器

## 0.14.0

- **实时状态刷新**：网关、Dashboard、终端三路服务在页面加载时并发预检，之后每 30 秒自动轮询
  - 每张入口卡片右上角新增彩色状态点：绿色（正常）/ 红色（不可用）/ 灰色闪烁（检查中）
  - 服务不可用时卡片自动灰显并禁止点击，恢复后自动解锁，无需刷新页面
  - 网关健康轮询结果一并更新顶部"网关状态"卡片
- **深色/浅色模式双支持**：新增 `<meta name="color-scheme" content="dark light">` 及 `@media (prefers-color-scheme: light)` CSS 变量覆盖
  - 浅色模式下背景改为白/浅蓝渐变，文字/边框全部重新调色，accent 绿色保留
  - 深色模式行为与之前完全一致
- **版本号可点击**：点击"Add-on 版本"字段直接跳到 GitHub Releases 页面查看发布说明
- **骨架屏加载动画**：页面初始化时"当前模型"和"网关状态"两个动态字段显示 shimmer 扫光动画，数据到达后自动消失，消除空白闪烁
- **移动端适配强化**：新增 480px 和 360px 断点
  - ≤480px：启动卡片强制单列，状态条保持 2 列
  - ≤360px：状态条也折叠为单列

## 0.13.1

- **修复控制台首页版本号硬编码**：`index.html` 中 "Add-on 版本" 字段长期显示 `v0.10.1`（从 v0.10.1 起从未更新）
  - `Dockerfile` 新增 `ENV ADDON_VERSION=${BUILD_VERSION}` 和 `ENV HERMES_UPSTREAM_LABEL`，将版本信息注入容器运行时环境
  - `index.html` 改为占位符 `{{ADDON_VERSION}}` / `{{HERMES_UPSTREAM}}`，不再硬编码
  - `server.py _serve_index` 在响应时读取环境变量完成替换，版本号每次 Rebuild 自动更新

## 0.13.0

- **配置页精简**：移除 6 个很少需要改的字段，配置页只保留真正有用的选项
  - 删除：`huggingface_api_key`、`hf_base_url`（HF 目前不支持 tool calling，这两个字段没有实际作用）
  - 删除：`auth_provider`（内部固定 `openai_web`，用户不需要改）
  - 删除：`openai_oauth_client_id`、`openai_oauth_redirect_uri`、`openai_oauth_scopes`（OAuth 参数有合理默认值，硬编码进 run.sh）
  - 保留：`llm_model`、三个 API key、`auth_mode`、`auth_storage_path`、`terminal_backend`、HA watch 参数、`messaging_cwd`、`api_server_key`
- **新增中文翻译** `translations/zh.yaml`：配置页 label/description 现在支持中文显示
- **精简英文翻译** `translations/en.yaml`：对应删除的字段一并移除，描述文字更简洁
- **`docs/ARCHITECTURE.md` 完整重写**：更新到 v0.11+ 布局（原文档还在描述 pre-v0.9 的 `/data` 路径，已完全过时）
- **新建 `docs/STORAGE.md`**：记录容器/宿主机路径映射、目录重要性分级、三种备份策略、跨版本/跨机器迁移步骤
- **新建 `hermes_agent/patches/README.md`**：说明 patches/ 目录的设计原则和 `ha_ws_url.py` 的完整背景，方便未来升级时判断是否可以删除
- **新增 GitHub Actions CI** (`.github/workflows/lint.yml`)：每次 push/PR 自动检查 bash 语法、Python 编译、run.sh 内嵌 Python 块、YAML 合法性、Dockerfile hadolint

## 0.12.0

- **Dockerfile 预编译 web UI**：`RUN cd /opt/hermes/web && npm install && npm run build` 在镜像 build 时就把 dashboard 前端编译进去，彻底解掉首启 `✗ Web UI npm install failed` 问题
  - 之前：node_modules 和 dist 在容器写入层，每次 Rebuild 清空，首启需要 30–60s npm 重装 + 上游 PATH/nvm bug 导致 npm 直接失败，`/panel/` 永远 502，靠手动 `npm install` 才能恢复
  - 之后：dist 已经在镜像里，dashboard 启动时检测到 dist 存在直接跳过 build，`/panel/` 立即可用
  - 非致命：若未来上游镜像没有 web/ 或 npm，`|| true` 保证不阻断构建，回退到首启 build 行为
- 升级上游 Hermes 镜像到 2026-04-23 `latest` 快照（digest `7ab9fc41…`，比 v2026.4.16 新 7 天），带入上游 PATH/nvm、gateway session 锁、D-Bus preflight 等修复
- 删除 `run.sh` 里 v0.9 时代的 `/opt/data` 死代码（符号链接农场，v0.11 后已无任何代码读取 `/opt/data`）

## 0.11.1

- 恢复 v0.9.11 在 v0.10.0 重写时丢掉的 `hermes dashboard` 启动诊断块
  - 启动时打印 `Starting hermes dashboard on 127.0.0.1:9119...`
  - `sleep 0.5` 后用 `kill -0 ${DASH_PID}` 探活，立即退出则在日志上方直接报 `WARNING: hermes dashboard exited immediately — /panel/ will be unavailable`
  - 如果 `--help` 都不通，提示 `this Hermes build has no hermes dashboard subcommand`
  - 针对常见首启失败场景（npm install 炸、上游没打 node、网络被墙 npmjs.org）给出下一步排查提示
- 纯诊断改动，无行为变化；如果 dashboard 能跑起来，输出只多两行日志

## 0.11.0

- **Breaking**: 规范化 add-on 存储布局，迁移到 HA 2023.11+ 标准 `addon_config` map type
  - `config.yaml`: `map` 从 `homeassistant_config + path:/config` 改为 `addon_config:rw`
  - 容器内挂载点仍是 `/config`，但宿主机位置从 `/homeassistant/addons_data/hermes-agent/` 变为 `/addon_configs/<slug>_hermes_agent/`（每个 add-on 独立隔离目录）
  - 去掉 `/config/addons_data/hermes-agent/` 多层嵌套，扁平化到 `/config/` 根：
    - `HERMES_HOME`: `/config/addons_data/hermes-agent/.hermes` → `/config/.hermes`
    - `messaging_cwd`: `/config/addons_data/hermes-agent/workspace` → `/config/workspace`
    - `auth_storage_path`: `/config/addons_data/hermes-agent/addon-state/auth` → `/config/auth`
  - 同步更新 `Dockerfile`、`run.sh`、`server.py`、`/etc/profile.d/hermes.sh`
- run.sh 增加一次性布局迁移：如果 `/config/addons_data/hermes-agent/` 存在（例如用户手工从旧位置拷贝进来），自动把内容上移到 `/config/` 根，幂等
- 升级迁移说明（SSH 到 HA OS 执行一次，老数据在旧宿主机路径下不会自动被 add-on 看到）：
  ```
  ls /addon_configs/                                    # 找到 <slug>_hermes_agent 实际目录名
  mkdir -p /addon_configs/<slug>_hermes_agent/
  cp -a /homeassistant/addons_data/hermes-agent/. /addon_configs/<slug>_hermes_agent/
  ```
  然后在 HA 里 Rebuild add-on。如果接受重新登录 OpenAI + 丢弃 workspace 历史，可以跳过拷贝，让 add-on 自己重新生成全部默认文件

## 0.10.4

- 再次修复 `MESSAGING_CWD` deprecation 警告（v0.10.2 的补丁不彻底）
  - 真因：v0.10.2 把 `export MESSAGING_CWD=...` 放进 `.addon-runtime`，run.sh source 后该变量进了**进程环境变量**。Hermes v0.10.0 的 deprecation 检查扫 `os.environ` 而不只是 `.env` 文件，所以即使 .env 干净也照样告警（措辞是 "found in .env" 但实际读的是 environ）
  - 修法：side 文件改用 `TTYD_CWD=...` 变量名（不与 Hermes 的遗留 env 冲突），bash 用 `sed` 提取后作为**局部变量**喂给 ttyd，不再 `export` 任何相关变量
  - ttyd 命令改用位置参数传递 cwd（`bash -c 'cd "$1" && exec bash -i' _ "${TTYD_CWD}"`），比 env var fallback 更健壮
  - 额外加一道 `unset MESSAGING_CWD` 做双保险，清掉从老 .env 里 source 进来的残留

## 0.10.3

- 修复 `hermes_ui/server.py` 中文字符串编码损坏导致的启动 SyntaxError
  - line 263 原本是 `f"代理请求失败：{type(exc).__name__}"`，被误当 GBK 重新编码后变成 `f"浠ｇ悊璇锋眰澶辫触锛歿type(exc).__name__}"`，`{` 被吞进 mojibake 导致 f-string 语法错误
  - ingress UI server 启动即崩，`/`、`/panel/`、`/ttyd/`、健康检查全部 502
- 一并还原：文件 BOM 去除、所有 `—` / `→` / `…` 等非 GBK Unicode 字符恢复
- 内嵌版本号从 `0.9.11` 对齐到 `0.10.3`

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
