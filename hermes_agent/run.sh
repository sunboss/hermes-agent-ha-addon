#!/usr/bin/env bash
# Hermes Agent add-on entrypoint.
#
# Layout:
#   /config                  — addon_config:rw mount
#                              host: /addon_configs/<slug>_hermes_agent/
#   /config/.hermes          — HERMES_HOME (sessions, config.yaml, memories, skills...)
#   /opt/hermes              — upstream install (HERMES_INSTALL_DIR)
#   /opt/hermes-ha-scripts   — runtime configuration scripts
#   /opt/hermes-ha-patches   — Ingress / PTY / WebSocket patches
#
# Architecture:
#   tini (PID 1)
#     ├─> nginx (port 8099 Ingress + port 9119 LAN)
#     ├─> hermes dashboard (127.0.0.1:9120)
#     └─> hermes gateway (foreground)

set -euo pipefail

export CONFIG_PATH=/data/options.json
export ADDON_STATE_ROOT=/config
export HERMES_HOME="${ADDON_STATE_ROOT}/.hermes"
export HOME="${ADDON_STATE_ROOT}"
export HERMES_INSTALL_DIR=/opt/hermes
export PATH="${HERMES_INSTALL_DIR}/.venv/bin:${PATH}"
export HERMES_PANEL_HOST=127.0.0.1
export HERMES_PANEL_PORT=9120

mkdir -p /data "${ADDON_STATE_ROOT}" "${HERMES_HOME}"

# ── 权限降级（root → hermes user）────────────────────────────────────────
if [ "$(id -u)" = "0" ] && [ "${HERMES_ADDON_PRIVILEGE_DROPPED:-}" != "1" ]; then
  python3 /opt/hermes-ha-scripts/configure.py
  python3 /opt/hermes-ha-patches/pty_auth_bypass.py || true
  python3 /opt/hermes-ha-patches/ingress_chunk_path.py || true
  python3 /opt/hermes-ha-scripts/patch-web-dist.py /opt/hermes/hermes_cli/web_dist/index.html || true

  chown -R hermes:hermes "${ADDON_STATE_ROOT}" /tmp/nginx_* 2>/dev/null || \
    echo "[run.sh] WARNING: chown failed; continuing" >&2

  export HERMES_ADDON_PRIVILEGE_DROPPED=1
  export HERMES_ADDON_CONFIGURED=1
  echo "[run.sh] Dropping root privileges to hermes (HERMES_HOME=${HERMES_HOME})..."
  if command -v gosu >/dev/null 2>&1; then
    exec gosu hermes "$0" "$@"
  fi
  for candidate in /command/s6-setuidgid /usr/bin/s6-setuidgid /bin/s6-setuidgid; do
    if [ -x "${candidate}" ]; then
      exec "${candidate}" hermes "$0" "$@"
    fi
  done
  echo "[run.sh] ERROR: gosu or s6-setuidgid not found." >&2
  exit 1
fi

# ── 非 root 启动兜底检查 ──────────────────────────────────────────────────
if [ "${HERMES_ADDON_CONFIGURED:-}" != "1" ]; then
  python3 /opt/hermes-ha-scripts/configure.py
fi

# ── 固定持久化的 Dashboard 会话 Token（与 nginx.conf 完全一致）─────────────
export HERMES_DASHBOARD_SESSION_TOKEN="${HERMES_DASHBOARD_SESSION_TOKEN:-hermes-ha-addon-persistent-session-token-v1}"

set -a
. "${HERMES_HOME}/.env"
set +a
unset MESSAGING_CWD

# ── 启动 hermes dashboard（127.0.0.1:9120）────────────────────────────────
echo "[run.sh] Starting hermes dashboard on 127.0.0.1:9120..."
hermes dashboard \
  --host 127.0.0.1 \
  --port 9120 \
  --no-open &
DASH_PID=$!
sleep 1
if ! kill -0 "${DASH_PID}" 2>/dev/null; then
  echo "[run.sh] WARNING: hermes dashboard exited immediately" >&2
else
  echo "[run.sh] hermes dashboard started (PID ${DASH_PID})"
fi

# ── 启动 nginx（Ingress 8099 + LAN 9119）─────────────────────────────────
echo "[run.sh] Starting nginx (Ingress :8099, LAN :9119)..."
mkdir -p /tmp/nginx_client_body /tmp/nginx_proxy_temp /tmp/nginx_fastcgi_temp /tmp/nginx_uwsgi_temp /tmp/nginx_scgi_temp 2>/dev/null || true
touch /tmp/nginx_error.log /tmp/nginx_access.log 2>/dev/null || true
nginx -c /etc/nginx/nginx.conf &
NGINX_PID=$!
sleep 0.5
if ! kill -0 "${NGINX_PID}" 2>/dev/null; then
  echo "[run.sh] ERROR: nginx failed to start; error log:" >&2
  cat /tmp/nginx_error.log >&2 || true
else
  echo "[run.sh] nginx started (PID ${NGINX_PID})"
  tail -F /tmp/nginx_error.log &
fi

# ── 增量同步内置技能库（保留用户自定义技能）──────────────────────────────
if [ -f "${HERMES_INSTALL_DIR}/tools/skills_sync.py" ]; then
  python3 "${HERMES_INSTALL_DIR}/tools/skills_sync.py" || true
fi

# ── 启动 hermes gateway（前台运行）──────────────────────────────────────
echo "[run.sh] Starting Hermes Agent gateway (HERMES_HOME=${HERMES_HOME})..."
exec hermes gateway run
