# Changelog

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
