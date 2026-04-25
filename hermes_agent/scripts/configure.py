#!/usr/bin/env python3
"""Render Hermes Agent runtime configuration from HA add-on options.

Invoked from run.sh on every container start.  Reads /data/options.json
(written by the HA Supervisor from the add-on's UI configuration), merges
it with any existing user state under ${HERMES_HOME}, and writes back:

  ${HERMES_HOME}/.env              — KEY=value for `set -a; . .env`
  ${HERMES_HOME}/config.yaml       — Hermes runtime config (model, terminal,
                                     platforms.homeassistant.extra)
  ${HERMES_HOME}/.addon-runtime    — TTYD_CWD=... (read by bash, never
                                     exported, see MESSAGING_CWD note below)
  ${AUTH_STORAGE_PATH}/session.json — auth state stub for first boot

Required environment (exported by run.sh):
  ADDON_STATE_ROOT     — /config (the add-on's per-instance config dir)
  HERMES_HOME          — ${ADDON_STATE_ROOT}/.hermes
  HERMES_INSTALL_DIR   — /opt/hermes (where upstream image lives)
  SUPERVISOR_TOKEN     — passed into HASS_TOKEN/HASS_URL for HA platform

Extracted from the inline `python3 - <<'PY'` heredoc in run.sh
(v2026.4.25.1+) so the configuration logic is editable, testable, and
greppable as a normal Python file.  The bash side just sources the
resulting .env and unsets the legacy MESSAGING_CWD.
"""
from __future__ import annotations

import json
import os
import secrets
import sys
from pathlib import Path

import yaml


def env_quote(value: str) -> str:
    """Quote a value for safe inclusion in a `KEY="..."` shell line."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def load_options() -> dict:
    config_path = Path("/data/options.json")
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def migrate_legacy_layout(addon_state_root: Path) -> None:
    """Lift v0.10.x nested layout up to v0.11.0+ flat layout.

    Old: /config/addons_data/hermes-agent/<stuff>
    New: /config/<stuff>

    No-op for fresh installs; only triggers if a user copied old state in
    manually.  Existing destinations are respected (we never overwrite).
    """
    legacy_root = addon_state_root / "addons_data" / "hermes-agent"
    if not legacy_root.is_dir():
        return
    for entry in legacy_root.iterdir():
        dest = addon_state_root / entry.name
        if dest.exists():
            continue
        entry.rename(dest)
    try:
        legacy_root.rmdir()
        (addon_state_root / "addons_data").rmdir()
    except OSError:
        # Non-empty (user placed unrelated files); leave alone.
        pass


def seed_default_files(install_dir: Path, hermes_home: Path) -> None:
    """Copy upstream example files into HERMES_HOME on first boot."""
    for source_name, target_name in (
        (".env.example", ".env"),
        ("cli-config.yaml.example", "config.yaml"),
    ):
        source = install_dir / source_name
        target = hermes_home / target_name
        if source.exists() and not target.exists():
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    soul_source = install_dir / "docker" / "SOUL.md"
    soul_target = hermes_home / "SOUL.md"
    if soul_source.exists() and not soul_target.exists():
        soul_target.write_text(soul_source.read_text(encoding="utf-8"), encoding="utf-8")


def read_existing_env(env_path: Path) -> dict[str, str]:
    env_map: dict[str, str] = {}
    if not env_path.exists():
        return env_map
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env_map[key] = value.strip().strip('"')
    return env_map


def write_env(env_path: Path, env_map: dict[str, str]) -> None:
    lines = ["# Managed by the Home Assistant add-on wrapper."]
    for key in sorted(env_map):
        lines.append(f"{key}={env_quote(env_map[key])}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_auth_session(auth_storage_path: Path, auth_mode: str, auth_provider: str) -> None:
    session_path = auth_storage_path / "session.json"
    state: dict = {}
    if session_path.exists():
        try:
            loaded = json.loads(session_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                state = loaded
        except json.JSONDecodeError:
            state = {}

    state["mode"] = auth_mode
    state["provider"] = auth_provider
    state.setdefault("updated_at", None)
    state.setdefault("session", None)
    state.setdefault("pending_login", None)
    state["status"] = (
        "not_required"
        if auth_mode == "api_key"
        else ("authenticated" if state.get("session") else "needs_login")
    )
    session_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_runtime_config(
    runtime_config_path: Path,
    *,
    llm_model: str,
    auth_mode: str,
    auth_provider: str,
    openrouter_key: str,
    openai_base_url: str,
    terminal_backend: str,
    messaging_cwd: Path,
    watch_all: bool,
    cooldown_seconds: int,
    watch_domains: list[str],
    watch_entities: list[str],
    ignore_entities: list[str],
) -> None:
    cfg: dict = {}
    if runtime_config_path.exists():
        loaded = yaml.safe_load(runtime_config_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            cfg = loaded

    model_cfg = cfg.get("model")
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
    cfg["model"] = model_cfg

    terminal_cfg = cfg.get("terminal")
    if not isinstance(terminal_cfg, dict):
        terminal_cfg = {}
    terminal_cfg["backend"] = terminal_backend
    terminal_cfg["cwd"] = str(messaging_cwd)
    cfg["terminal"] = terminal_cfg

    platforms = cfg.get("platforms")
    if not isinstance(platforms, dict):
        platforms = {}
    cfg["platforms"] = platforms

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
        yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def main() -> int:
    options = load_options()

    addon_state_root = Path(os.environ["ADDON_STATE_ROOT"])
    hermes_home = Path(os.environ["HERMES_HOME"])
    install_dir = Path(os.environ["HERMES_INSTALL_DIR"])

    # v0.11.0+ flat layout: /config IS the per-addon config dir.
    default_workspace = addon_state_root / "workspace"
    default_auth_root = addon_state_root / "auth"

    migrate_legacy_layout(addon_state_root)

    messaging_cwd = Path(options.get("messaging_cwd") or str(default_workspace))
    auth_storage_path = Path(options.get("auth_storage_path") or str(default_auth_root))
    auth_mode = str(options.get("auth_mode") or "api_key")
    auth_provider = "openai_web"  # was a config option until upstream v0.13.0
    llm_model = str(options.get("llm_model") or "gpt-5.4")
    terminal_backend = str(options.get("terminal_backend") or "local")

    # OAuth fields removed from the add-on UI in v0.13.0 (sensible defaults).
    openai_oauth_client_id = ""
    openai_oauth_redirect_uri = "http://127.0.0.1:1455/auth/callback"
    openai_oauth_scopes = "openid profile email offline_access"

    watch_domains = [str(item) for item in (options.get("watch_domains") or [])]
    watch_entities = [str(item) for item in (options.get("watch_entities") or [])]
    ignore_entities = [str(item) for item in (options.get("ignore_entities") or [])]
    watch_all = bool(options.get("watch_all", False))
    cooldown_seconds = int(options.get("cooldown_seconds", 30))

    for d in (addon_state_root, hermes_home, messaging_cwd, auth_storage_path):
        d.mkdir(parents=True, exist_ok=True)
    for sub in ("cron", "sessions", "logs", "memories", "skills", "hooks", "skins", "plans"):
        (hermes_home / sub).mkdir(parents=True, exist_ok=True)

    seed_default_files(install_dir, hermes_home)

    env_path = hermes_home / ".env"
    env_map = read_existing_env(env_path)

    env_map["HASS_URL"] = "http://supervisor/core"
    env_map["SUPERVISOR_TOKEN"] = os.environ.get("SUPERVISOR_TOKEN", "")
    env_map["HASS_TOKEN"] = os.environ.get("SUPERVISOR_TOKEN", "")
    env_map["HERMES_HOME"] = str(hermes_home)
    env_map["HERMES_STATE_ROOT"] = str(addon_state_root)

    # MESSAGING_CWD is deprecated in Hermes v0.10.0+. The gateway scans both
    # .env AND os.environ for it and prints a warning if found, so we:
    #   1. Strip it from .env here.
    #   2. `unset MESSAGING_CWD` in run.sh after sourcing .env.
    #   3. Pass the workspace path to ttyd via the side file .addon-runtime
    #      using the distinct name TTYD_CWD, read into a non-exported bash
    #      local. See docs/UPGRADE_LOG.md §v0.10.4.
    env_map.pop("MESSAGING_CWD", None)
    env_map.pop("LLM_MODEL", None)

    env_map["AUTH_MODE"] = auth_mode
    env_map["AUTH_PROVIDER"] = auth_provider
    env_map["AUTH_STORAGE_PATH"] = str(auth_storage_path)
    env_map["OPENAI_OAUTH_CLIENT_ID"] = openai_oauth_client_id
    env_map["OPENAI_OAUTH_REDIRECT_URI"] = openai_oauth_redirect_uri
    env_map["OPENAI_OAUTH_SCOPES"] = openai_oauth_scopes
    env_map["API_SERVER_ENABLED"] = "true"
    env_map["API_SERVER_HOST"] = "127.0.0.1"
    env_map["API_SERVER_PORT"] = "8642"
    env_map["API_SERVER_KEY"] = str(
        options.get("api_server_key") or env_map.get("API_SERVER_KEY") or secrets.token_urlsafe(24)
    )
    env_map["API_SERVER_MODEL_NAME"] = llm_model
    env_map["OPENAI_SHIM_MODEL"] = llm_model
    env_map["HERMES_TTYD_PORT"] = os.environ.get("HERMES_TTYD_PORT", "7681")
    env_map["GATEWAY_ALLOW_ALL_USERS"] = "true"

    for option_key, env_key in (
        ("openrouter_api_key", "OPENROUTER_API_KEY"),
        ("openai_base_url", "OPENAI_BASE_URL"),
        ("openai_api_key", "OPENAI_API_KEY"),
    ):
        value = options.get(option_key)
        if value not in (None, ""):
            env_map[env_key] = str(value)

    openrouter_key = str(options.get("openrouter_api_key") or "")
    openai_base_url = str(options.get("openai_base_url") or "")

    if auth_mode == "web_login" and auth_provider == "openai_web":
        env_map["OPENAI_BASE_URL"] = "http://127.0.0.1:8099/shim/v1"
        env_map["OPENAI_API_KEY"] = env_map.get("OPENAI_API_KEY") or "web-login-session"

    write_env(env_path, env_map)
    update_auth_session(auth_storage_path, auth_mode, auth_provider)
    write_runtime_config(
        hermes_home / "config.yaml",
        llm_model=llm_model,
        auth_mode=auth_mode,
        auth_provider=auth_provider,
        openrouter_key=openrouter_key,
        openai_base_url=openai_base_url,
        terminal_backend=terminal_backend,
        messaging_cwd=messaging_cwd,
        watch_all=watch_all,
        cooldown_seconds=cooldown_seconds,
        watch_domains=watch_domains,
        watch_entities=watch_entities,
        ignore_entities=ignore_entities,
    )

    # Side file for bash to source TTYD_CWD as a NON-exported local. Using
    # `export` would re-introduce the deprecated MESSAGING_CWD-style
    # warning under a different name, so the value is read by run.sh via
    # `sed` and assigned to a bash local instead.
    (hermes_home / ".addon-runtime").write_text(
        f"TTYD_CWD={env_quote(str(messaging_cwd))}\n",
        encoding="utf-8",
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
