#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from auth_bridge import get_live_session

SHIM_MODEL_NAME = os.environ.get("OPENAI_SHIM_MODEL", "gpt-5.4")
OPENAI_CODEX_RESPONSES_URL = os.environ.get(
    "OPENAI_CODEX_RESPONSES_URL",
    "https://chatgpt.com/backend-api/codex/responses",
)
OPENAI_CODEX_ORIGINATOR = os.environ.get("OPENAI_CODEX_ORIGINATOR", "hermes-ha-addon")
OPENAI_CODEX_VERSION = os.environ.get("OPENAI_CODEX_VERSION", "0.6")
OPENAI_CODEX_USER_AGENT = os.environ.get(
    "OPENAI_CODEX_USER_AGENT",
    "Mozilla/5.0 (X11; Linux aarch64) HermesAgentHA/0.6",
)


def _normalize_model(model: str) -> str:
    value = (model or "").strip()
    if not value:
        return SHIM_MODEL_NAME
    if "/" in value:
        return value.split("/", 1)[1].strip() or SHIM_MODEL_NAME
    return value


def _role_content(role: str, text: str) -> dict[str, Any]:
    return {
        "type": "message",
        "role": role,
        "content": [{"type": "input_text", "text": text}],
    }


def _messages_to_input(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    input_items: list[dict[str, Any]] = []
    for message in messages:
        role = str(message.get("role") or "user")
        content = message.get("content")
        if isinstance(content, str):
            text = content.strip()
        elif isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    maybe_text = item.get("text") or item.get("content")
                    if isinstance(maybe_text, str):
                        parts.append(maybe_text)
            text = "\n".join(part.strip() for part in parts if part and part.strip())
        else:
            text = ""
        if not text:
            continue
        normalized_role = role if role in {"system", "user", "assistant", "developer"} else "user"
        input_items.append(_role_content(normalized_role, text))
    return input_items


def _extract_output_text(payload: dict[str, Any]) -> str:
    collected: list[str] = []
    for item in payload.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []) or []:
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                collected.append(text.strip())
            elif content.get("type") == "output_text":
                maybe_text = content.get("text") or content.get("value")
                if isinstance(maybe_text, str) and maybe_text.strip():
                    collected.append(maybe_text.strip())
    if collected:
        return "\n\n".join(collected)
    maybe_text = payload.get("output_text")
    if isinstance(maybe_text, str) and maybe_text.strip():
        return maybe_text.strip()
    return ""


def _headers(session: dict[str, Any]) -> dict[str, str]:
    account_id = session.get("account_id") or ""
    headers = {
        "Authorization": f"Bearer {session['access_token']}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "originator": OPENAI_CODEX_ORIGINATOR,
        "openai-version": OPENAI_CODEX_VERSION,
        "User-Agent": OPENAI_CODEX_USER_AGENT,
    }
    if account_id:
        headers["chatgpt-account-id"] = str(account_id)
    return headers


def list_models() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {
                "id": SHIM_MODEL_NAME,
                "object": "model",
                "owned_by": "openai-codex-web-login",
            }
        ],
    }


def chat_completions(request_payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    session = get_live_session()
    requested_model = request_payload.get("model")
    raw_model = requested_model if isinstance(requested_model, str) and requested_model.strip() else SHIM_MODEL_NAME
    model = _normalize_model(raw_model)
    input_items = _messages_to_input(request_payload.get("messages") or [])
    if not input_items:
        return 400, {
            "error": {
                "message": "At least one message is required.",
                "type": "invalid_request_error",
            }
        }

    upstream_payload = {
        "model": model,
        "input": input_items,
        "store": False,
        "stream": False,
    }
    if "temperature" in request_payload:
        upstream_payload["temperature"] = request_payload.get("temperature")
    if "max_tokens" in request_payload:
        upstream_payload["max_output_tokens"] = request_payload.get("max_tokens")

    request = urllib.request.Request(
        OPENAI_CODEX_RESPONSES_URL,
        data=json.dumps(upstream_payload).encode("utf-8"),
        headers=_headers(session),
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            upstream = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = {"error": {"message": f"upstream_http_{exc.code}", "type": "upstream_error"}}
        return exc.code, payload if isinstance(payload, dict) else {"error": {"message": str(payload), "type": "upstream_error"}}
    except Exception as exc:
        return 502, {
            "error": {
                "message": f"Upstream Codex request failed: {exc}",
                "type": "upstream_error",
            }
        }

    assistant_text = _extract_output_text(upstream)
    finish_reason = "stop" if upstream.get("status") in (None, "completed") else upstream.get("status")
    return 200, {
        "id": upstream.get("id") or f"chatcmpl-web-{os.urandom(4).hex()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": assistant_text,
                },
                "finish_reason": finish_reason,
            }
        ],
        "usage": upstream.get("usage") or {},
        "_codex_upstream": upstream,
    }
