#!/usr/bin/env bash
# run.sh  —  Hermes Agent HA Add-on: Container Entrypoint
# =========================================================
# Version: 0.9.9  (Hermes upstream v2026.4.13 / v0.9.0)
#
# Startup sequence
# ----------------
# 1. Export environment constants so child processes inherit them.
# 2. Run the Python bootstrap block (inline heredoc):
#      a. Read /data/options.json (written by the Home Assistant supervisor).
#      b. Create required directory tree under /data.
#      c. Copy .env.example and config.yaml.example on first boot.
#      d. Patch /data/.env with HA-specific overrides (HASS_URL, SUPERVISOR_TOKEN,
#         API_SERVER_KEY, model, auth settings, HuggingFace credentials, etc.).
#      e. Write /data/auth/session.json with the current auth mode/state.
#      f. Patch /data/config.yaml with terminal backend, platform settings,
#         and entity watch configuration.
# 3. Source /data/.env so the gateway process inherits all variables.
# 4. Start ttyd terminal server in background.
# 5. Start the Python ingress UI server (server.py) in background.
# 6. Bypass upstream entrypoint.sh (which hardcodes HERMES_HOME=/opt/data
#    and would break our auth.json/config.yaml lookup) and run hermes directly.
#
# Options read from /data/options.json (set via HA add-on UI)
# ------------------------------------------------------------
#   llm_model            Model ID (default: NousResearch/Hermes-4-14B)
#   openrouter_api_key   OpenRouter API key
#   openai_base_url      OpenAI-compatible base URL
#   openai_api_key       OpenAI-compatible API key
#   huggingface_api_key  HuggingFace Inference API key
#   hf_base_url          HF Inference base URL (default: https://api-inference.huggingface.co/v1)
#   auth_mode            "api_key" (default) or "web_login"
#   auth_provider        "openai_web" (default) or "custom"
#   terminal_backend     local | docker | ssh | modal | daytona | singularity
#   watch_domains        List of HA domains to watch for state changes
#   watch_entities       List of specific HA entity IDs to watch
#   ignore_entities      List of HA entity IDs to always ignore
#   watch_all            Boolean — forward ALL HA state changes (use with care)
#   cooldown_seconds     Minimum seconds between repeated events (0-3600)
#   messaging_cwd        Working directory for Hermes sessions
#   api_server_key       Bearer token for Hermes gateway API (auto-generated if blank)
set -euo pipefail

# ── 1. Environment constants ──────────────────────────────────────────────────
export HOME=/data
export HERMES_HOME=/data
export HERMES_INSTALL_DIR=/opt/hermes
export PATH="${HERMES_INSTALL_DIR}/.venv/bin:${PATH}"
export HERMES_UI_PORT=8099
export HERMES_UI_DIR=/opt/hermes-ha-ui
export HERMES_TTYD_PORT="${HERMES_TTYD_PORT:-7681}"

mkdir -p /data /data/workspace /data/auth

# ── 2. Python bootstrap: read options, patch .env and config.yaml ─────────────
python3 - <<'PY'
import json
import os
import secrets
from pathlib import Path

import yaml


def env_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


options_path = Path("/data/options.json")
options = json.loads(options_path.read_text(encoding="utf-8")) if options_path.exists() else {}

hermes_home = Path(os.environ["HERMES_HOME"])
install_dir = Path(os.environ["HERMES_INSTALL_DIR"])
hermes_home.mkdir(parents=True, exist_ok=True)

messaging_cwd = options.get("messaging_cwd") or "/data/workspace"
auth_mode = str(options.get("auth_mode") or "api_key")
auth_provider = str(options.get("auth_provider") or "openai_web")
auth_storage_path = Path(options.get("auth_storage_path") or "/data/auth")
openai_oauth_client_id = str(options.get("openai_oauth_client_id") or "")
openai_oauth_redirect_uri = str(options.get("openai_oauth_redirect_uri") or "http://127.0.0.1:1455/auth/callback")
openai_oauth_scopes = str(options.get("openai_oauth_scopes") or "openid profile email offline_access")
llm_model = str(options.get("llm_model") or "")

Path(messaging_cwd).mkdir(parents=True, exist_ok=True)
auth_storage_path.mkdir(parents=True, exist_ok=True)

for dirname in ("cron", "sessions", "logs", "hooks", "memories", "skills", "skins", "plans", "workspace", "home"):
    (hermes_home / dirname).mkdir(parents=True, exist_ok=True)

for source_name, target_name in ((".env.example", ".env"), ("cli-config.yaml.example", "config.yaml")):
    source = install_dir / source_name
    target = hermes_home / target_name
    if source.exists() and not target.exists():
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

soul_source = install_dir / "docker" / "SOUL.md"
soul_target = hermes_home / "SOUL.md"
if soul_source.exists() and not soul_target.exists():
    soul_target.write_text(soul_source.read_text(encoding="utf-8"), encoding="utf-8")

env_map = {}
env_path = hermes_home / ".env"
if env_path.exists():
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env_map[key] = value.strip().strip('"')

env_map["HASS_URL"] = "http://supervisor/core"
env_map["SUPERVISOR_TOKEN"] = os.environ.get("SUPERVISOR_TOKEN", "")
env_map["HASS_TOKEN"] = os.environ.get("SUPERVISOR_TOKEN", "")
env_map["MESSAGING_CWD"] = messaging_cwd
env_map["AUTH_MODE"] = auth_mode
env_map["AUTH_PROVIDER"] = auth_provider
env_map["AUTH_STORAGE_PATH"] = str(auth_storage_path)
env_map["OPENAI_OAUTH_CLIENT_ID"] = openai_oauth_client_id
env_map["OPENAI_OAUTH_REDIRECT_URI"] = openai_oauth_redirect_uri
env_map["OPENAI_OAUTH_SCOPES"] = openai_oauth_scopes
env_map["API_SERVER_ENABLED"] = "true"
env_map["API_SERVER_HOST"] = "127.0.0.1"
env_map["API_SERVER_PORT"] = "8642"
env_map["API_SERVER_KEY"] = str(options.get("api_server_key") or env_map.get("API_SERVER_KEY") or secrets.token_urlsafe(24))
env_map["OPENAI_SHIM_MODEL"] = llm_model or env_map.get("OPENAI_SHIM_MODEL") or "NousResearch/Hermes-4-14B"
# API_SERVER_MODEL_NAME controls what the Hermes gateway returns from GET /v1/models.
# Set it to the configured llm_model so the UI model picker shows the real model name.
env_map["API_SERVER_MODEL_NAME"] = llm_model or env_map.get("API_SERVER_MODEL_NAME") or "NousResearch/Hermes-4-14B"
env_map["HERMES_TTYD_PORT"] = os.environ.get("HERMES_TTYD_PORT", "7681")
# Allow all users — the HA add-on is a trusted internal component; HA Ingress
# handles external auth, so we don't need the gateway to enforce its own allowlist.
env_map["GATEWAY_ALLOW_ALL_USERS"] = "true"

huggingface_api_key = str(options.get("huggingface_api_key") or "")
hf_base_url = str(options.get("hf_base_url") or "https://api-inference.huggingface.co/v1")

# NOTE: Hermes v2026.4.13 removes the LLM_MODEL env var.  The model is now
# configured exclusively via config.yaml (model.default / model.provider).
# We still honour the llm_model HA option — it is written to config.yaml
# below, not to the env.
for option_key, env_key in (
    ("openrouter_api_key", "OPENROUTER_API_KEY"),
    ("openai_base_url", "OPENAI_BASE_URL"),
    ("openai_api_key", "OPENAI_API_KEY"),
    ("huggingface_api_key", "HUGGINGFACE_API_KEY"),
    ("hf_base_url", "HF_BASE_URL"),
):
    value = options.get(option_key)
    if value not in (None, ""):
        env_map[env_key] = str(value)

# Strip any stale LLM_MODEL carried over from older .env files.
env_map.pop("LLM_MODEL", None)

# When a HuggingFace API key is provided and no explicit OpenAI base URL is set,
# wire up the HuggingFace Inference API as the OpenAI-compatible endpoint so that
# Hermes can reach NousResearch models (Hermes-4-14B, Hermes-4-70B, etc.) directly.
if huggingface_api_key and not options.get("openai_base_url") and not options.get("openrouter_api_key"):
    env_map.setdefault("OPENAI_BASE_URL", hf_base_url)
    env_map.setdefault("OPENAI_API_KEY", huggingface_api_key)

if auth_mode == "web_login" and auth_provider == "openai_web":
    env_map["OPENAI_BASE_URL"] = "http://127.0.0.1:8099/shim/v1"
    env_map["OPENAI_API_KEY"] = env_map.get("OPENAI_API_KEY") or "web-login-session"

env_lines = ["# Managed by the Home Assistant add-on wrapper."]
for key in sorted(env_map):
    env_lines.append(f"{key}={env_quote(env_map[key])}")
env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")

session_path = auth_storage_path / "session.json"
auth_state = {}
if session_path.exists():
    try:
        loaded = json.loads(session_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            auth_state = loaded
    except json.JSONDecodeError:
        auth_state = {}

auth_state["mode"] = auth_mode
auth_state["provider"] = auth_provider
auth_state.setdefault("updated_at", None)
auth_state.setdefault("session", None)
auth_state.setdefault("pending_login", None)
if auth_mode == "api_key":
    auth_state["status"] = "not_required"
else:
    auth_state["status"] = "authenticated" if auth_state.get("session") else "needs_login"
session_path.write_text(json.dumps(auth_state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

terminal_backend = str(options.get("terminal_backend") or "local")
watch_domains = options.get("watch_domains") or []
watch_entities = options.get("watch_entities") or []
ignore_entities = options.get("ignore_entities") or []
watch_all = bool(options.get("watch_all", False))
cooldown_seconds = int(options.get("cooldown_seconds", 30))

config_path = hermes_home / "config.yaml"
config = {}
if config_path.exists():
    loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if isinstance(loaded, dict):
        config = loaded

# Hermes v2026.4.13 expects `model` as a mapping (default / provider / base_url),
# not a plain string.  Preserve any existing provider block; only update the
# default field when the HA option provides a model name.
model_cfg = config.get("model")
if not isinstance(model_cfg, dict):
    model_cfg = {}
if llm_model:
    model_cfg["default"] = llm_model
# Preserve the OpenAI Codex defaults on first boot so the web-login flow
# lights up immediately after an `hermes auth login openai-codex`.
model_cfg.setdefault("default", llm_model or "gpt-5.4")
model_cfg.setdefault("provider", "openai-codex")
model_cfg.setdefault("base_url", "https://chatgpt.com/backend-api/codex")
config["model"] = model_cfg

terminal = config.get("terminal")
if not isinstance(terminal, dict):
    terminal = {}
config["terminal"] = terminal
terminal["backend"] = terminal_backend
terminal["cwd"] = messaging_cwd

platforms = config.get("platforms")
if not isinstance(platforms, dict):
    platforms = {}
config["platforms"] = platforms

homeassistant = platforms.get("homeassistant")
if not isinstance(homeassistant, dict):
    homeassistant = {}
platforms["homeassistant"] = homeassistant
homeassistant["enabled"] = True

extra = homeassistant.get("extra")
if not isinstance(extra, dict):
    extra = {}
homeassistant["extra"] = extra
extra["watch_all"] = watch_all
extra["cooldown_seconds"] = cooldown_seconds
extra["watch_domains"] = [str(item) for item in watch_domains]
extra["watch_entities"] = [str(item) for item in watch_entities]
extra["ignore_entities"] = [str(item) for item in ignore_entities]

config_path.write_text(
    yaml.safe_dump(config, sort_keys=False, allow_unicode=True),
    encoding="utf-8",
)
PY

# ── 3. Source .env so the gateway inherits all variables ─────────────────────
set -a
. /data/.env
set +a

# ── 4. Start ttyd terminal server (background) ───────────────────────────────
# --base-path /ttyd  must match the proxy prefix used in server.py (_is_ttyd_request)
# /bin/bash -lc loads .profile / .bash_profile so the Hermes venv PATH is active
#
# NOTE: ttyd is installed by apt to /usr/bin/ttyd, NOT /usr/local/bin/ttyd.
# Use `command -v ttyd` to resolve the actual path at runtime so this works
# regardless of where the package installs the binary.
TTYD_BIN="$(command -v ttyd 2>/dev/null || true)"
if [ -z "${TTYD_BIN}" ]; then
  echo "[run.sh] WARNING: ttyd not found in PATH — terminal will be unavailable" >&2
else
  echo "[run.sh] Starting ttyd (${TTYD_BIN}) on port ${HERMES_TTYD_PORT}..."
  "${TTYD_BIN}" \
    --port "${HERMES_TTYD_PORT}" \
    --base-path /ttyd \
    --writable \
    /bin/bash -lc 'cd "${MESSAGING_CWD:-/data/workspace}" && exec /bin/bash -i' &
  TTYD_PID=$!
  # Give ttyd a moment to bind the port and check it didn't exit immediately
  sleep 0.5
  if ! kill -0 "${TTYD_PID}" 2>/dev/null; then
    echo "[run.sh] WARNING: ttyd exited immediately — terminal will be unavailable" >&2
  else
    echo "[run.sh] ttyd started (PID ${TTYD_PID})"
  fi
fi

# ── 5. Start ingress UI server (background) ──────────────────────────────────
# server.py listens on HERMES_UI_PORT (8099) and proxies /api/** to the gateway.
# It also serves the static UI files from HERMES_UI_DIR and handles /auth/** locally.
python3 "${HERMES_UI_DIR}/server.py" &

# ── 6. Launch Hermes gateway (foreground — becomes the main process) ──────────
#
# IMPORTANT: We do NOT call /opt/hermes/docker/entrypoint.sh here.  That script
# hardcodes `HERMES_HOME=/opt/data` at the top, which would override our
# `HERMES_HOME=/data` export and cause the gateway to look for auth.json,
# config.yaml and .env in the WRONG directory (the container writable layer,
# which is wiped on every container recreation).
#
# We replicate the one-time bootstrap steps that the upstream entrypoint.sh
# performs (skills_sync) and then exec hermes directly so HERMES_HOME=/data
# is respected and all state persists in the HA add-on data volume.
#
# `hermes gateway run` forces true foreground execution — required inside a
# Docker container.  `hermes gateway` alone tries to daemonise and exits.
if [ -f "${HERMES_INSTALL_DIR}/tools/skills_sync.py" ]; then
  python3 "${HERMES_INSTALL_DIR}/tools/skills_sync.py" || true
fi

# Safety fallback: if an older Hermes release still expects /opt/data to
# exist, symlink the key state files so both paths resolve to /data.
if [ -d /opt/data ]; then
  for f in auth.json config.yaml .env SOUL.md; do
    [ -e "/opt/data/$f" ] && [ ! -L "/opt/data/$f" ] && rm -f "/opt/data/$f"
    [ -e "/data/$f" ] && ln -sf "/data/$f" "/opt/data/$f" 2>/dev/null || true
  done
fi

echo "[run.sh] Starting Hermes Agent gateway (HERMES_HOME=${HERMES_HOME})..."
exec hermes gateway run