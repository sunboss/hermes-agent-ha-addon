# Changelog

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
