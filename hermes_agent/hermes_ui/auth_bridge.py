#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUTH_MODE = os.environ.get("AUTH_MODE", "api_key")
AUTH_PROVIDER = os.environ.get("AUTH_PROVIDER", "openai_web")
AUTH_STORAGE_PATH = Path(os.environ.get("AUTH_STORAGE_PATH", "/data/auth"))
SESSION_PATH = AUTH_STORAGE_PATH / "session.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_state() -> dict[str, Any]:
    return {
        "mode": AUTH_MODE,
        "provider": AUTH_PROVIDER,
        "status": "not_required" if AUTH_MODE == "api_key" else "needs_login",
        "session": None,
        "updated_at": None,
    }


def load_state(create_missing: bool = True) -> dict[str, Any]:
    if create_missing:
        AUTH_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    if not SESSION_PATH.exists():
        return {}
    try:
        loaded = json.loads(SESSION_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def save_state(state: dict[str, Any]) -> None:
    AUTH_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now_iso()
    SESSION_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def ensure_state() -> dict[str, Any]:
    AUTH_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    state = load_state(create_missing=False)
    if not state:
        state = _default_state()
        save_state(state)
        return state

    state["mode"] = AUTH_MODE
    state["provider"] = AUTH_PROVIDER
    if AUTH_MODE == "api_key":
        state["status"] = "not_required"
    elif state.get("session"):
        state["status"] = state.get("status") or "authenticated"
    else:
        state["status"] = "needs_login"
    save_state(state)
    return state


def clear_session() -> dict[str, Any]:
    state = ensure_state()
    state["session"] = None
    state["status"] = "not_required" if AUTH_MODE == "api_key" else "needs_login"
    save_state(state)
    return state


def get_status() -> dict[str, Any]:
    state = ensure_state()
    has_session = bool(state.get("session"))
    status = state.get("status") or ("not_required" if AUTH_MODE == "api_key" else "needs_login")
    ready = AUTH_MODE == "api_key" or status == "authenticated"
    login_supported = AUTH_MODE == "web_login" and AUTH_PROVIDER == "openai_web"
    if AUTH_MODE == "api_key":
        message = "API key mode is active. No browser login session is required."
    elif login_supported:
        message = "Web login bridge is scaffolded. Session storage and status APIs are ready; provider login wiring is the next step."
    else:
        message = "Custom web login mode is configured, but no provider bridge is wired yet."
    return {
        "mode": AUTH_MODE,
        "provider": AUTH_PROVIDER,
        "status": status,
        "ready": ready,
        "has_session": has_session,
        "login_supported": login_supported,
        "storage_path": str(AUTH_STORAGE_PATH),
        "session_path": str(SESSION_PATH),
        "message": message,
        "updated_at": state.get("updated_at"),
    }


def start_login() -> tuple[int, dict[str, Any]]:
    status = get_status()
    if AUTH_MODE != "web_login":
        return 400, {
            "error": "web_login_not_enabled",
            "message": "auth_mode must be set to web_login before starting a browser login flow.",
            "status": status,
        }
    return 501, {
        "error": "login_bridge_not_implemented",
        "message": "The browser login bridge skeleton is ready, but the provider-specific OpenClaw-style flow is not wired yet.",
        "status": status,
    }