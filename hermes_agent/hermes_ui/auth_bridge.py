#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

AUTH_MODE = os.environ.get("AUTH_MODE", "api_key")
AUTH_PROVIDER = os.environ.get("AUTH_PROVIDER", "openai_web")
AUTH_STORAGE_PATH = Path(os.environ.get("AUTH_STORAGE_PATH", "/data/auth"))
SESSION_PATH = AUTH_STORAGE_PATH / "session.json"

OPENAI_OAUTH_CLIENT_ID = os.environ.get("OPENAI_OAUTH_CLIENT_ID", "").strip()
OPENAI_OAUTH_REDIRECT_URI = os.environ.get("OPENAI_OAUTH_REDIRECT_URI", "http://127.0.0.1:1455/auth/callback").strip()
OPENAI_OAUTH_SCOPES = os.environ.get("OPENAI_OAUTH_SCOPES", "openid profile email offline_access").strip()
OPENAI_AUTH_URL = "https://auth.openai.com/oauth/authorize"
OPENAI_TOKEN_URL = "https://auth.openai.com/oauth/token"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _default_state() -> dict[str, Any]:
    return {
        "mode": AUTH_MODE,
        "provider": AUTH_PROVIDER,
        "status": "not_required" if AUTH_MODE == "api_key" else "needs_login",
        "session": None,
        "pending_login": None,
        "updated_at": None,
    }


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _expires_in_seconds(expires_at: str | None) -> int | None:
    parsed = _parse_timestamp(expires_at)
    if parsed is None:
        return None
    return int((parsed - _now()).total_seconds())


def _oauth_configured() -> bool:
    return bool(OPENAI_OAUTH_CLIENT_ID and OPENAI_OAUTH_REDIRECT_URI and OPENAI_OAUTH_SCOPES)


def _pkce_verifier() -> str:
    return secrets.token_urlsafe(72)


def _pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _decode_jwt_claims(token: str | None) -> dict[str, Any]:
    if not token or token.count(".") < 2:
        return {}
    try:
        payload = token.split(".")[1]
        padding = "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode((payload + padding).encode("ascii"))
        claims = json.loads(decoded.decode("utf-8"))
    except Exception:
        return {}
    return claims if isinstance(claims, dict) else {}


def _extract_account_id(access_token: str | None) -> str | None:
    claims = _decode_jwt_claims(access_token)
    for key in (
        "account_id",
        "accountId",
        "https://api.openai.com/account_id",
        "https://auth.openai.com/account_id",
        "sub",
    ):
        value = claims.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


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


def _session_status(session: dict[str, Any] | None) -> str:
    if not session:
        return "needs_login"
    expires_at = session.get("expires_at")
    remaining = _expires_in_seconds(expires_at)
    if remaining is not None and remaining <= 0:
        return "expired"
    return "authenticated"


def _sanitize_pending_login(pending_login: dict[str, Any] | None) -> dict[str, Any] | None:
    if not pending_login:
        return None
    return {
        "created_at": pending_login.get("created_at"),
        "expires_at": pending_login.get("expires_at"),
        "redirect_uri": pending_login.get("redirect_uri"),
        "scopes": pending_login.get("scopes"),
        "state": pending_login.get("state"),
    }


def ensure_state() -> dict[str, Any]:
    AUTH_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    state = load_state(create_missing=False)
    if not state:
        state = _default_state()
        save_state(state)
        return state

    state["mode"] = AUTH_MODE
    state["provider"] = AUTH_PROVIDER
    state.setdefault("session", None)
    state.setdefault("pending_login", None)

    if AUTH_MODE == "api_key":
        state["status"] = "not_required"
    else:
        state["status"] = _session_status(state.get("session"))
    save_state(state)
    return state


def clear_session() -> dict[str, Any]:
    state = ensure_state()
    state["session"] = None
    state["pending_login"] = None
    state["status"] = "not_required" if AUTH_MODE == "api_key" else "needs_login"
    save_state(state)
    return state


def _status_message(status: str, oauth_ready: bool) -> str:
    if AUTH_MODE == "api_key":
        return "API key mode is active. No browser login session is required."
    if AUTH_PROVIDER != "openai_web":
        return "Custom web login mode is selected, but no provider-specific bridge is wired yet."
    if not oauth_ready:
        return "OpenAI web login mode is enabled, but the OAuth client configuration is incomplete. Fill in the client ID, redirect URI, and scopes first."
    if status == "authenticated":
        return "OpenAI Codex web login session is active. Hermes can now reuse the stored browser auth profile."
    if status == "expired":
        return "The stored web login session has expired. Refresh it or start a new login flow."
    return "OpenAI Codex web login is ready. Start the PKCE flow, complete the browser sign-in, then paste the callback URL here."


def get_status() -> dict[str, Any]:
    state = ensure_state()
    session = state.get("session")
    pending_login = state.get("pending_login")
    status = state.get("status") or ("not_required" if AUTH_MODE == "api_key" else "needs_login")
    expires_at = None
    expires_in = None
    account_id = None
    if isinstance(session, dict):
        expires_at = session.get("expires_at")
        expires_in = _expires_in_seconds(expires_at)
        account_id = session.get("account_id")

    oauth_ready = _oauth_configured() if AUTH_PROVIDER == "openai_web" else False
    ready = AUTH_MODE == "api_key" or status == "authenticated"
    return {
        "mode": AUTH_MODE,
        "provider": AUTH_PROVIDER,
        "status": status,
        "ready": ready,
        "has_session": bool(session),
        "login_supported": AUTH_MODE == "web_login" and AUTH_PROVIDER == "openai_web",
        "oauth_configured": oauth_ready,
        "storage_path": str(AUTH_STORAGE_PATH),
        "session_path": str(SESSION_PATH),
        "pending_login": _sanitize_pending_login(pending_login if isinstance(pending_login, dict) else None),
        "account_id": account_id,
        "expires_at": expires_at,
        "expires_in": expires_in,
        "message": _status_message(status, oauth_ready),
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
    if AUTH_PROVIDER != "openai_web":
        return 501, {
            "error": "provider_not_supported",
            "message": "Only the OpenAI Codex web login provider is wired in this build.",
            "status": status,
        }
    if not _oauth_configured():
        return 400, {
            "error": "oauth_config_missing",
            "message": "Missing OAuth client configuration. Set openai_oauth_client_id, openai_oauth_redirect_uri, and openai_oauth_scopes first.",
            "status": status,
        }

    state = ensure_state()
    verifier = _pkce_verifier()
    login_state = secrets.token_urlsafe(24)
    created_at = _now()
    pending_login = {
        "state": login_state,
        "code_verifier": verifier,
        "code_challenge": _pkce_challenge(verifier),
        "redirect_uri": OPENAI_OAUTH_REDIRECT_URI,
        "scopes": OPENAI_OAUTH_SCOPES,
        "created_at": created_at.isoformat(),
        "expires_at": (created_at + timedelta(minutes=15)).isoformat(),
    }
    state["pending_login"] = pending_login
    state["status"] = "awaiting_callback"
    save_state(state)

    params = urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": OPENAI_OAUTH_CLIENT_ID,
            "redirect_uri": OPENAI_OAUTH_REDIRECT_URI,
            "scope": OPENAI_OAUTH_SCOPES,
            "state": login_state,
            "code_challenge": pending_login["code_challenge"],
            "code_challenge_method": "S256",
        }
    )
    auth_url = f"{OPENAI_AUTH_URL}?{params}"
    return 200, {
        "message": "Browser login URL generated. Complete the sign-in, then paste the full callback URL back into the bridge.",
        "auth_url": auth_url,
        "manual_exchange_required": True,
        "status": get_status(),
    }


def _exchange_token(form_data: dict[str, str]) -> dict[str, Any]:
    encoded = urllib.parse.urlencode(form_data).encode("utf-8")
    request = urllib.request.Request(
        OPENAI_TOKEN_URL,
        data=encoded,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("token_response_not_object")
    return payload


def complete_login(callback_url: str | None = None, code: str | None = None, state_value: str | None = None) -> tuple[int, dict[str, Any]]:
    status = get_status()
    if AUTH_MODE != "web_login":
        return 400, {
            "error": "web_login_not_enabled",
            "message": "auth_mode must be set to web_login before completing a browser login flow.",
            "status": status,
        }
    if AUTH_PROVIDER != "openai_web":
        return 501, {
            "error": "provider_not_supported",
            "message": "Only the OpenAI Codex web login provider is wired in this build.",
            "status": status,
        }
    if not _oauth_configured():
        return 400, {
            "error": "oauth_config_missing",
            "message": "Missing OAuth client configuration. Set openai_oauth_client_id, openai_oauth_redirect_uri, and openai_oauth_scopes first.",
            "status": status,
        }

    bridge_state = ensure_state()
    pending_login = bridge_state.get("pending_login") if isinstance(bridge_state.get("pending_login"), dict) else None
    if not pending_login:
        return 400, {
            "error": "no_pending_login",
            "message": "No login attempt is waiting for a callback. Start a new login flow first.",
            "status": status,
        }

    if callback_url:
        parsed = urllib.parse.urlsplit(callback_url)
        query = urllib.parse.parse_qs(parsed.query)
        code = code or (query.get("code", [None])[0])
        state_value = state_value or (query.get("state", [None])[0])
        callback_error = query.get("error", [None])[0]
        if callback_error:
            return 400, {
                "error": "oauth_callback_error",
                "message": f"The provider redirected back with an error: {callback_error}",
                "status": status,
            }

    if not code:
        return 400, {
            "error": "missing_code",
            "message": "No authorization code was found. Paste the full callback URL or provide the code directly.",
            "status": status,
        }
    if state_value != pending_login.get("state"):
        return 400, {
            "error": "state_mismatch",
            "message": "The returned state token did not match the pending login attempt. Start the flow again.",
            "status": status,
        }

    try:
        token_payload = _exchange_token(
            {
                "grant_type": "authorization_code",
                "client_id": OPENAI_OAUTH_CLIENT_ID,
                "code": code,
                "redirect_uri": str(pending_login.get("redirect_uri") or OPENAI_OAUTH_REDIRECT_URI),
                "code_verifier": str(pending_login.get("code_verifier") or ""),
            }
        )
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = {"error": f"http_{exc.code}"}
        return 502, {
            "error": "token_exchange_failed",
            "message": "OpenAI token exchange failed.",
            "details": payload,
            "status": status,
        }
    except Exception as exc:
        return 502, {
            "error": "token_exchange_failed",
            "message": f"OpenAI token exchange failed: {exc}",
            "status": status,
        }

    access_token = token_payload.get("access_token")
    refresh_token = token_payload.get("refresh_token")
    if not isinstance(access_token, str) or not access_token.strip():
        return 502, {
            "error": "token_exchange_incomplete",
            "message": "OpenAI did not return an access token.",
            "details": token_payload,
            "status": status,
        }

    expires_in_raw = token_payload.get("expires_in")
    try:
        expires_in = int(expires_in_raw) if expires_in_raw is not None else None
    except (TypeError, ValueError):
        expires_in = None

    obtained_at = _now()
    expires_at = (obtained_at + timedelta(seconds=expires_in)).isoformat() if expires_in else None
    bridge_state["session"] = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": token_payload.get("token_type") or "Bearer",
        "scope": token_payload.get("scope") or OPENAI_OAUTH_SCOPES,
        "account_id": _extract_account_id(access_token),
        "obtained_at": obtained_at.isoformat(),
        "expires_at": expires_at,
        "expires_in": expires_in,
    }
    bridge_state["pending_login"] = None
    bridge_state["status"] = "authenticated"
    save_state(bridge_state)
    return 200, {
        "message": "OpenAI Codex web login completed successfully.",
        "status": get_status(),
    }


def refresh_session() -> tuple[int, dict[str, Any]]:
    status = get_status()
    if AUTH_MODE != "web_login":
        return 400, {
            "error": "web_login_not_enabled",
            "message": "auth_mode must be set to web_login before refreshing a browser login session.",
            "status": status,
        }
    if AUTH_PROVIDER != "openai_web":
        return 501, {
            "error": "provider_not_supported",
            "message": "Only the OpenAI Codex web login provider is wired in this build.",
            "status": status,
        }
    if not _oauth_configured():
        return 400, {
            "error": "oauth_config_missing",
            "message": "Missing OAuth client configuration. Set openai_oauth_client_id, openai_oauth_redirect_uri, and openai_oauth_scopes first.",
            "status": status,
        }

    bridge_state = ensure_state()
    session = bridge_state.get("session") if isinstance(bridge_state.get("session"), dict) else None
    if not session or not session.get("refresh_token"):
        return 400, {
            "error": "missing_refresh_token",
            "message": "No refresh token is stored. Start a new browser login flow instead.",
            "status": status,
        }

    try:
        token_payload = _exchange_token(
            {
                "grant_type": "refresh_token",
                "client_id": OPENAI_OAUTH_CLIENT_ID,
                "refresh_token": str(session.get("refresh_token")),
            }
        )
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = {"error": f"http_{exc.code}"}
        return 502, {
            "error": "token_refresh_failed",
            "message": "OpenAI token refresh failed.",
            "details": payload,
            "status": status,
        }
    except Exception as exc:
        return 502, {
            "error": "token_refresh_failed",
            "message": f"OpenAI token refresh failed: {exc}",
            "status": status,
        }

    access_token = token_payload.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        return 502, {
            "error": "token_refresh_incomplete",
            "message": "OpenAI did not return a refreshed access token.",
            "details": token_payload,
            "status": status,
        }

    expires_in_raw = token_payload.get("expires_in")
    try:
        expires_in = int(expires_in_raw) if expires_in_raw is not None else None
    except (TypeError, ValueError):
        expires_in = None

    obtained_at = _now()
    expires_at = (obtained_at + timedelta(seconds=expires_in)).isoformat() if expires_in else None
    session.update(
        {
            "access_token": access_token,
            "refresh_token": token_payload.get("refresh_token") or session.get("refresh_token"),
            "token_type": token_payload.get("token_type") or session.get("token_type") or "Bearer",
            "scope": token_payload.get("scope") or session.get("scope") or OPENAI_OAUTH_SCOPES,
            "account_id": _extract_account_id(access_token) or session.get("account_id"),
            "obtained_at": obtained_at.isoformat(),
            "expires_at": expires_at,
            "expires_in": expires_in,
        }
    )
    bridge_state["session"] = session
    bridge_state["status"] = "authenticated"
    save_state(bridge_state)
    return 200, {
        "message": "OpenAI Codex web login session refreshed successfully.",
        "status": get_status(),
    }
