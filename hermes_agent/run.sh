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
export HERMES_PANEL_HOST="${HERMES_PANEL_HOST:-127.0.0.1}"
export HERMES_PANEL_PORT="${HERMES_PANEL_PORT:-9119}"

mkdir -p /data "${ADDON_STATE_ROOT}" "${HERMES_HOME}"

# Render .env / config.yaml / .addon-runtime / auth/session.json.
# See scripts/configure.py for everything this writes.
python3 /opt/hermes-ha-scripts/configure.py

set -a
. "${HERMES_HOME}/.env"
set +a

# Belt-and-suspenders: MESSAGING_CWD is deprecated in upstream and the
# gateway scans os.environ for it (not just .env).  configure.py strips
# it from .env, this clears the inherited process environment too.
unset MESSAGING_CWD

# Read TTYD_CWD from the side file as a bash LOCAL (no `export`).  An
# exported MESSAGING_CWD-style variable would re-trigger the deprecation
# warning even under a renamed key, so we keep this strictly local.
TTYD_CWD=""
if [ -f "${HERMES_HOME}/.addon-runtime" ]; then
  TTYD_CWD="$(sed -n 's/^TTYD_CWD="\(.*\)"$/\1/p' "${HERMES_HOME}/.addon-runtime")"
fi
: "${TTYD_CWD:=${ADDON_STATE_ROOT}/workspace}"

TTYD_BIN="$(command -v ttyd 2>/dev/null || true)"
if [ -n "${TTYD_BIN}" ]; then
  "${TTYD_BIN}" \
    --port "${HERMES_TTYD_PORT}" \
    --base-path /ttyd \
    --writable \
    /bin/bash -c 'cd "$1" && exec /bin/bash -il' _launch "${TTYD_CWD}" &
fi

python3 "${HERMES_UI_DIR}/server.py" &

# Launch upstream `hermes dashboard` on loopback; server.py reverse-proxies
# /panel/** to this host:port.  The 0.5s sanity check below catches the
# common first-boot failure mode where dashboard tries to npm install/build
# the web UI and exits non-zero (missing node, blocked registry, write-layer
# permission errors).  Restored in v0.11.1 after regressing in v0.10.0.
if hermes dashboard --help >/dev/null 2>&1; then
  echo "[run.sh] Starting hermes dashboard on ${HERMES_PANEL_HOST}:${HERMES_PANEL_PORT}..."
  hermes dashboard \
    --host "${HERMES_PANEL_HOST}" \
    --port "${HERMES_PANEL_PORT}" \
    --no-open &
  DASH_PID=$!
  sleep 0.5
  if ! kill -0 "${DASH_PID}" 2>/dev/null; then
    echo "[run.sh] WARNING: hermes dashboard exited immediately — /panel/ will be unavailable" >&2
    echo "[run.sh]          check the lines above for the upstream error (commonly npm install / web build failures)" >&2
  else
    echo "[run.sh] hermes dashboard started (PID ${DASH_PID})"
  fi
else
  echo "[run.sh] NOTICE: this Hermes build has no \`hermes dashboard\` subcommand — /panel/ will return 502" >&2
fi

if [ -f "${HERMES_INSTALL_DIR}/tools/skills_sync.py" ]; then
  python3 "${HERMES_INSTALL_DIR}/tools/skills_sync.py" || true
fi

echo "[run.sh] Starting Hermes Agent gateway (HERMES_HOME=${HERMES_HOME})..."
exec hermes gateway run
