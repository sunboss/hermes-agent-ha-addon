#!/usr/bin/env bash
# Hermes Agent add-on entrypoint.
#
# Layout:
#   /config                  — addon_config:rw mount, host path
#                              /addon_configs/<slug>_hermes_agent/
#   /config/.hermes          — HERMES_HOME (sessions, .env, config.yaml)
#   /opt/hermes              — upstream install (HERMES_INSTALL_DIR)
#   /opt/hermes-ha-ui        — our ingress proxy (server.py)
#   /opt/hermes-ha-scripts   — build-time + runtime helper scripts
#
# All option-driven file rendering is done by scripts/configure.py — keeping
# this script a thin orchestrator (env exports, source .env, fork ttyd /
# UI / dashboard, exec gateway).
set -euo pipefail

export CONFIG_PATH=/data/options.json
export ADDON_STATE_ROOT=/config
export HERMES_HOME="${ADDON_STATE_ROOT}/.hermes"
export HOME="${ADDON_STATE_ROOT}"
export HERMES_INSTALL_DIR=/opt/hermes
export PATH="${HERMES_INSTALL_DIR}/.venv/bin:${PATH}"
export HERMES_UI_PORT=8099
export HERMES_UI_DIR=/opt/hermes-ha-ui
export HERMES_TTYD_PORT="${HERMES_TTYD_PORT:-7681}"
export HERMES_PANEL_HOST=127.0.0.1
export HERMES_PANEL_PORT=9120
export NATIVE_PROXY_HOST=0.0.0.0
export NATIVE_PROXY_PORT=9119

mkdir -p /data "${ADDON_STATE_ROOT}" "${HERMES_HOME}"

# Upstream refuses to run `hermes gateway` as root inside the official Docker
# image. HA Supervisor's /data/options.json is root-readable in some installs,
# so render config before dropping privileges; then re-exec this wrapper as the
# image's unprivileged `hermes` user so gateway, dashboard, ttyd, and our
# ingress UI share the same file ownership.
if [ "$(id -u)" = "0" ] && [ "${HERMES_ADDON_PRIVILEGE_DROPPED:-}" != "1" ]; then
  python3 /opt/hermes-ha-scripts/configure.py

# Auto-sync live version from config.yaml into UI
if [ -f /opt/hermes-ha-scripts/bake-version.py ]; then
  python3 /opt/hermes-ha-scripts/bake-version.py || true
fi

  chown -R hermes:hermes "${ADDON_STATE_ROOT}" 2>/dev/null || \
    echo "[run.sh] WARNING: chown ${ADDON_STATE_ROOT} failed; continuing" >&2
  export HERMES_ADDON_PRIVILEGE_DROPPED=1
  export HERMES_ADDON_CONFIGURED=1
  echo "[run.sh] Dropping root privileges to hermes (HERMES_HOME=${HERMES_HOME})..."
  if command -v gosu >/dev/null 2>&1; then
    exec gosu hermes "$0" "$@"
  fi
  S6_SETUIDGID="$(command -v s6-setuidgid 2>/dev/null || true)"
  if [ -z "${S6_SETUIDGID}" ]; then
    for candidate in /command/s6-setuidgid /usr/bin/s6-setuidgid /bin/s6-setuidgid; do
      if [ -x "${candidate}" ]; then
        S6_SETUIDGID="${candidate}"
        break
      fi
    done
  fi
  if [ -n "${S6_SETUIDGID}" ]; then
    exec "${S6_SETUIDGID}" hermes "$0" "$@"
  fi
  echo "[run.sh] ERROR: gosu or /command/s6-setuidgid is required to drop from root to the hermes user." >&2
  exit 1
fi

# Render .env / config.yaml / .addon-runtime / auth/session.json.
# See scripts/configure.py for everything this writes.
if [ "${HERMES_ADDON_CONFIGURED:-}" != "1" ]; then
  python3 /opt/hermes-ha-scripts/configure.py

# Auto-sync live version from config.yaml into UI
if [ -f /opt/hermes-ha-scripts/bake-version.py ]; then
  python3 /opt/hermes-ha-scripts/bake-version.py || true
fi

fi

set -a
. "${HERMES_HOME}/.env"
set +a

# Belt-and-suspenders: MESSAGING_CWD is deprecated in upstream and the
# gateway scans os.environ for it (not just .env).  configure.py strips
# it from .env, this clears the inherited process environment too.
unset MESSAGING_CWD

python3 "${HERMES_UI_DIR}/server.py" &

# Launch upstream `hermes dashboard` on loopback 127.0.0.1:9120
# Running on loopback prevents Hermes from failing with "Refusing to bind dashboard to 0.0.0.0"
if hermes dashboard --help >/dev/null 2>&1; then
  echo "[run.sh] Starting upstream hermes dashboard on 127.0.0.1:9120..."
  hermes dashboard \
    --host 127.0.0.1 \
    --port 9120 \
    --no-open &
  DASH_PID=$!
  sleep 0.5
  if ! kill -0 "${DASH_PID}" 2>/dev/null; then
    echo "[run.sh] WARNING: hermes dashboard exited immediately" >&2
  else
    echo "[run.sh] hermes dashboard started on 127.0.0.1:9120 (PID ${DASH_PID})"
  fi
fi

# Launch native_proxy on 0.0.0.0:9119 to provide zero-friction, direct LAN access
if [ -f "${HERMES_UI_DIR}/native_proxy.py" ]; then
  echo "[run.sh] Starting native proxy on 0.0.0.0:9119 -> 127.0.0.1:9120..."
  python3 "${HERMES_UI_DIR}/native_proxy.py" &
fi

if [ -f "${HERMES_INSTALL_DIR}/tools/skills_sync.py" ]; then
  python3 "${HERMES_INSTALL_DIR}/tools/skills_sync.py" || true
fi

echo "[run.sh] Starting Hermes Agent gateway (HERMES_HOME=${HERMES_HOME})..."
exec hermes gateway run
