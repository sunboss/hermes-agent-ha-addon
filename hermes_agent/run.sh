#!/usr/bin/env bash
set -euo pipefail

export CONFIG_PATH=/data/options.json
export HA_CONFIG_ROOT=/config
export ADDON_STATE_ROOT="${HA_CONFIG_ROOT}/addons_data/hermes-agent"
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

python3 - <<'PY'
import json
import os
import secrets
from pathlib import Path

import yaml


def env_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


config_path = Path("/data/options.json")
options = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}

ha_config_root = Path(os.environ["HA_CONFIG_ROOT"])
addon_state_root = Path(os.environ["ADDON_STATE_ROOT"])
hermes_home = Path(os.environ["HERMES_HOME"])
install_dir = Path(os.environ["HERMES_INSTALL_DIR"])

default_workspace = addon_state_root / "workspace"
default_auth_root = addon_state_root / "addon-state" / "auth"

messaging_cwd = Path(options.get("messaging_cwd") or str(default_workspace))
auth_storage_path = Path(options.get("auth_storage_path") or str(default_auth_root))
auth_mode = str(options.get("auth_mode") or "api_key")
auth_provider = str(options.get("auth_provider") or "openai_web")
llm_model = str(options.get("llm_model") or "gpt-5.4")
openai_oauth_client_id = str(options.get("openai_oauth_client_id") or "")
openai_oauth_redirect_uri = str(options.get("openai_oauth_redirect_uri") or "http://127.0.0.1:1455/auth/callback")
openai_oauth_scopes = str(options.get("openai_oauth_scopes") or "openid profile email offline_access")
watch_domains = [str(item) for item in (options.get("watch_domains") or [])]
watch_entities = [str(item) for item in (options.get("watch_entities") or [])]
ignore_entities = [str(item) for item in (options.get("ignore_entities") or [])]
watch_all = bool(options.get("watch_all", False))
cooldown_seconds = int(options.get("cooldown_seconds", 30))

addon_state_root.mkdir(parents=True, exist_ok=True)
hermes_home.mkdir(parents=True, exist_ok=True)
messaging_cwd.mkdir(parents=True, exist_ok=True)
auth_storage_path.mkdir(parents=True, exist_ok=True)

for dirname in ("cron", "sessions", "logs", "memories", "skills", "hooks", "skins", "plans"):
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

env_map: dict[str, str] = {}
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
env_map["HERMES_HOME"] = str(hermes_home)
env_map["HERMES_STATE_ROOT"] = str(addon_state_root)
# NOTE: MESSAGING_CWD is deprecated in Hermes v0.10.0.  The gateway now
# expects `terminal.cwd` in config.yaml (written further down) and scans
# both `.env` AND os.environ for the legacy name, printing a warning
# whenever it finds a match.  We:
#   1. Pop it from env_map here so the regenerated .env never has it.
#   2. `unset MESSAGING_CWD` in the bash parent (after sourcing .env)
#      so it doesn't live in the process environment either.
#   3. Communicate the workspace path to ttyd via a distinct variable
#      name (TTYD_CWD) written to ${HERMES_HOME}/.addon-runtime and read
#      as a LOCAL bash variable — never exported.
# See UPGRADE_LOG §v0.10.4 for the full backstory.
env_map.pop("MESSAGING_CWD", None)
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
env_map["API_SERVER_MODEL_NAME"] = llm_model
env_map["OPENAI_SHIM_MODEL"] = llm_model
env_map["HERMES_TTYD_PORT"] = os.environ.get("HERMES_TTYD_PORT", "7681")
env_map["GATEWAY_ALLOW_ALL_USERS"] = "true"

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

env_map.pop("LLM_MODEL", None)

hf_key = str(options.get("huggingface_api_key") or "")
hf_base_url = str(options.get("hf_base_url") or "https://api-inference.huggingface.co/v1")
openrouter_key = str(options.get("openrouter_api_key") or "")
openai_base_url = str(options.get("openai_base_url") or "")

if hf_key and not openrouter_key and not openai_base_url:
    env_map.setdefault("OPENAI_BASE_URL", hf_base_url)
    env_map.setdefault("OPENAI_API_KEY", hf_key)

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
auth_state["status"] = "not_required" if auth_mode == "api_key" else ("authenticated" if auth_state.get("session") else "needs_login")
session_path.write_text(json.dumps(auth_state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

runtime_config_path = hermes_home / "config.yaml"
runtime_config: dict = {}
if runtime_config_path.exists():
    loaded = yaml.safe_load(runtime_config_path.read_text(encoding="utf-8"))
    if isinstance(loaded, dict):
        runtime_config = loaded

model_cfg = runtime_config.get("model")
if not isinstance(model_cfg, dict):
    model_cfg = {}
model_cfg["default"] = llm_model or model_cfg.get("default") or "gpt-5.4"
if auth_mode == "web_login" and auth_provider == "openai_web":
    model_cfg.setdefault("provider", "openai-codex")
    model_cfg.setdefault("base_url", "https://chatgpt.com/backend-api/codex")
elif openrouter_key:
    model_cfg.setdefault("provider", "openrouter")
elif openai_base_url:
    model_cfg["base_url"] = openai_base_url
elif hf_key:
    model_cfg["base_url"] = hf_base_url
runtime_config["model"] = model_cfg

terminal_cfg = runtime_config.get("terminal")
if not isinstance(terminal_cfg, dict):
    terminal_cfg = {}
terminal_cfg["backend"] = str(options.get("terminal_backend") or "local")
terminal_cfg["cwd"] = str(messaging_cwd)
runtime_config["terminal"] = terminal_cfg

platforms = runtime_config.get("platforms")
if not isinstance(platforms, dict):
    platforms = {}
runtime_config["platforms"] = platforms

ha_platform = platforms.get("homeassistant")
if not isinstance(ha_platform, dict):
    ha_platform = {}
ha_platform["enabled"] = True
extra = ha_platform.get("extra")
if not isinstance(extra, dict):
    extra = {}
extra["watch_all"] = watch_all
extra["cooldown_seconds"] = cooldown_seconds
extra["watch_domains"] = watch_domains
extra["watch_entities"] = watch_entities
extra["ignore_entities"] = ignore_entities
ha_platform["extra"] = extra
platforms["homeassistant"] = ha_platform

runtime_config_path.write_text(
    yaml.safe_dump(runtime_config, sort_keys=False, allow_unicode=True),
    encoding="utf-8",
)

# Emit the resolved messaging cwd to a side file for bash to pick up.  This
# MUST NOT use `export` — Hermes v0.10.0's deprecation check scans the
# process environment (not just .env), so any variable named MESSAGING_CWD
# in os.environ will trigger the "deprecated in .env" warning even when
# .env itself is clean.  We write a plain VAR=value line and read it
# in bash via a non-exporting read, so ttyd gets the path it needs
# without polluting the Hermes gateway's environment.
addon_runtime_path = hermes_home / ".addon-runtime"
addon_runtime_path.write_text(
    f'TTYD_CWD={env_quote(str(messaging_cwd))}\n',
    encoding="utf-8",
)
PY

set -a
. "${HERMES_HOME}/.env"
set +a

# Belt-and-suspenders: make absolutely sure MESSAGING_CWD is not in the
# process environment before we hand off to ttyd / Hermes.  An older build
# (v0.10.1 / v0.10.2) exported MESSAGING_CWD via .addon-runtime which made
# Hermes v0.10.0 flag it as deprecated even though .env was clean.  Clear
# it unconditionally — the new side file uses TTYD_CWD instead.
unset MESSAGING_CWD

# Read TTYD_CWD from the side file without exporting it to the rest of the
# environment.  `sh -c 'eval ...'` would also work; a bare `read` over a
# here-doc is simpler and avoids any quoting surprises.
TTYD_CWD=""
if [ -f "${HERMES_HOME}/.addon-runtime" ]; then
  # Matches `TTYD_CWD="..."` and extracts the quoted value.
  TTYD_CWD="$(sed -n 's/^TTYD_CWD="\(.*\)"$/\1/p' "${HERMES_HOME}/.addon-runtime")"
fi
: "${TTYD_CWD:=${ADDON_STATE_ROOT}/workspace}"

TTYD_BIN="$(command -v ttyd 2>/dev/null || true)"
if [ -n "${TTYD_BIN}" ]; then
  "${TTYD_BIN}" \
    --port "${HERMES_TTYD_PORT}" \
    --base-path /ttyd \
    --writable \
    /bin/bash -c 'cd "$1" && exec /bin/bash -i' _launch "${TTYD_CWD}" &
fi

python3 "${HERMES_UI_DIR}/server.py" &

if hermes dashboard --help >/dev/null 2>&1; then
  hermes dashboard \
    --host "${HERMES_PANEL_HOST}" \
    --port "${HERMES_PANEL_PORT}" \
    --no-open &
fi

if [ -f "${HERMES_INSTALL_DIR}/tools/skills_sync.py" ]; then
  python3 "${HERMES_INSTALL_DIR}/tools/skills_sync.py" || true
fi

mkdir -p /opt/data
for file_name in auth.json config.yaml .env SOUL.md; do
  if [ -e "${HERMES_HOME}/${file_name}" ]; then
    ln -sf "${HERMES_HOME}/${file_name}" "/opt/data/${file_name}" 2>/dev/null || true
  fi
done

echo "[run.sh] Starting Hermes Agent gateway (HERMES_HOME=${HERMES_HOME})..."
exec hermes gateway run
