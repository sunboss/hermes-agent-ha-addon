#!/usr/bin/env bash
set -euo pipefail

export HOME=/data
export HERMES_HOME=/data
export HERMES_INSTALL_DIR=/opt/hermes
export PATH="${HERMES_INSTALL_DIR}/.venv/bin:${PATH}"

mkdir -p /data /data/workspace

python3 - <<'PY'
import json
import os
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
Path(messaging_cwd).mkdir(parents=True, exist_ok=True)

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
env_map["API_SERVER_ENABLED"] = "true" if options.get("api_server_enabled") else "false"

for option_key, env_key in (
    ("llm_model", "LLM_MODEL"),
    ("openrouter_api_key", "OPENROUTER_API_KEY"),
    ("openai_base_url", "OPENAI_BASE_URL"),
    ("openai_api_key", "OPENAI_API_KEY"),
    ("api_server_key", "API_SERVER_KEY"),
):
    value = options.get(option_key)
    if value not in (None, ""):
        env_map[env_key] = str(value)

env_lines = ["# Managed by the Home Assistant add-on wrapper."]
for key in sorted(env_map):
    env_lines.append(f"{key}={env_quote(env_map[key])}")
env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")

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

if options.get("llm_model"):
    config["model"] = str(options["llm_model"])

terminal = config.get("terminal")
if not isinstance(terminal, dict):
    terminal = {}
config["terminal"] = terminal
terminal["backend"] = "local"
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
    yaml.safe_dump(config, sort_keys=False, allow_unicode=False),
    encoding="utf-8",
)
PY

echo "Starting Hermes Agent gateway via official entrypoint..."
exec /opt/hermes/docker/entrypoint.sh gateway
