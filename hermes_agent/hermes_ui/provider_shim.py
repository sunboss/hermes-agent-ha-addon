#!/usr/bin/env python3
"""
hermes_ui/provider_shim.py  —  Hermes Agent HA Add-on: Provider Shim
=====================================================================
Version: 0.9.0

Bridges the Ingress UI's /shim/v1/* endpoints to the correct upstream LLM
provider.  The shim is intentionally restricted to loopback-only access
(enforced by server.py) because it forwards stored OAuth tokens.

Provider routing logic (_choose_provider)
-----------------------------------------
  1. HuggingFace Inference API  — selected when HUGGINGFACE_API_KEY is set
     and the requested model belongs to the NousResearch namespace.
     Endpoint: HF_BASE_URL/chat/completions  (OpenAI-compatible TGI endpoint)

  2. OpenAI-compatible endpoint  — selected when OPENAI_BASE_URL + OPENAI_API_KEY
     are set (covers self-hosted vLLM, LM Studio, OpenRouter, etc.).
     Endpoint: OPENAI_BASE_URL/chat/completions

  3. OpenAI Codex web-login  — fallback when neither API key path is available.
     Requires an active PKCE session managed by auth_bridge.py.
     Endpoint: OPENAI_CODEX_RESPONSES_URL

NousResearch Hermes 4 ChatML defaults
--------------------------------------
All Hermes 4 series models use ChatML format with <|im_start|> tokens.
Reference: https://huggingface.co/NousResearch

  temperature = 0.6
  top_p       = 0.95
  top_k       = 20    (HuggingFace TGI / vLLM extra param; ignored by strict OpenAI)
  max_tokens  = 8192

Supported Hermes 4 model IDs (NOUSRESEARCH_MODELS list)
--------------------------------------------------------
  NousResearch/Hermes-4-14B    (default; 14B, fine-tuned on Qwen 3 14B)
  NousResearch/Hermes-4-70B    (70B)
  NousResearch/Hermes-4-405B   (405B FP8)
  NousResearch/Hermes-4.3-36B  (36B, latest)

Environment variables
---------------------
  OPENAI_SHIM_MODEL            Default model when none specified (default: Hermes-4-14B)
  HUGGINGFACE_API_KEY          HF Inference API key (enables HF provider path)
  HF_BASE_URL                  HF Inference base URL (default: https://api-inference.huggingface.co/v1)
  OPENAI_BASE_URL              OpenAI-compatible base URL
  OPENAI_API_KEY               OpenAI-compatible API key
  HERMES_TEMPERATURE           Override default temperature (default: 0.6)
  HERMES_TOP_P                 Override default top_p      (default: 0.95)
  HERMES_TOP_K                 Override default top_k      (default: 20)
  HERMES_MAX_TOKENS            Override default max_tokens (default: 8192)

Public API (consumed by server.py)
-----------------------------------
  list_models()         → dict          OpenAI-shaped model list for the UI picker
  chat_completions()    → (int, dict)   Route a chat completion request upstream
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from auth_bridge import get_live_session

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SHIM_MODEL_NAME = os.environ.get("OPENAI_SHIM_MODEL", "NousResearch/Hermes-4-14B")

# HuggingFace Inference API (OpenAI-compatible endpoint)
HF_BASE_URL = os.environ.get(
    "HF_BASE_URL",
    "https://api-inference.huggingface.co/v1",
).rstrip("/")
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY", "")

# Fallback: OpenAI-compatible base URL (may also be a self-hosted vLLM / LM Studio etc.)
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "").rstrip("/")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# OpenAI Codex web-login backend (used only in web_login mode)
OPENAI_CODEX_RESPONSES_URL = os.environ.get(
    "OPENAI_CODEX_RESPONSES_URL",
    "https://chatgpt.com/backend-api/codex/responses",
)
OPENAI_CODEX_ORIGINATOR = os.environ.get("OPENAI_CODEX_ORIGINATOR", "hermes-ha-addon")
OPENAI_CODEX_VERSION = os.environ.get("OPENAI_CODEX_VERSION", "0.7")
OPENAI_CODEX_USER_AGENT = os.environ.get(
    "OPENAI_CODEX_USER_AGENT",
    "Mozilla/5.0 (X11; Linux aarch64) HermesAgentHA/0.7",
)

# NousResearch Hermes 4 ChatML sampling defaults
# Reference: https://huggingface.co/NousResearch
HERMES_DEFAULT_TEMPERATURE = float(os.environ.get("HERMES_TEMPERATURE", "0.6"))
HERMES_DEFAULT_TOP_P = float(os.environ.get("HERMES_TOP_P", "0.95"))
HERMES_DEFAULT_TOP_K = int(os.environ.get("HERMES_TOP_K", "20"))
HERMES_DEFAULT_MAX_TOKENS = int(os.environ.get("HERMES_MAX_TOKENS", "8192"))  # Hermes 4 supports 32k+ context

# Known NousResearch Hermes 4 model IDs (used for provider routing and model listing)
NOUSRESEARCH_MODELS = [
    "NousResearch/Hermes-4-14B",
    "NousResearch/Hermes-4-70B",
    "NousResearch/Hermes-4-405B",
    "NousResearch/Hermes-4.3-36B",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_model(model: str) -> str:
    value = (model or "").strip()
    if not value:
        return SHIM_MODEL_NAME
    # Strip leading provider prefix like "openai/" or "huggingface/"
    if "/" in value and not value.startswith("NousResearch/"):
        parts = value.split("/", 1)
        # Keep NousResearch/* as-is; strip other vendor prefixes only
        if parts[0].lower() not in ("nousresearch",):
            return parts[1].strip() or SHIM_MODEL_NAME
    return value


def _is_nousresearch_model(model: str) -> bool:
    """Return True if the model ID belongs to the NousResearch namespace."""
    normalized = _normalize_model(model)
    return normalized.startswith("NousResearch/") or any(
        normalized.lower() == m.lower() for m in NOUSRESEARCH_MODELS
    )


def _choose_provider(model: str) -> str:
    """Return 'huggingface', 'openai_compat', or 'codex_web'."""
    if HUGGINGFACE_API_KEY and _is_nousresearch_model(model):
        return "huggingface"
    if OPENAI_BASE_URL and OPENAI_API_KEY:
        return "openai_compat"
    # Fall back to Codex web-login shim (requires active session)
    return "codex_web"


# ---------------------------------------------------------------------------
# HuggingFace / OpenAI-compatible chat completions
# ---------------------------------------------------------------------------

def _openai_compat_chat(
    base_url: str,
    api_key: str,
    model: str,
    request_payload: dict[str, Any],
) -> tuple[int, dict[str, Any]]:
    """Call an OpenAI-compatible /chat/completions endpoint.

    Applies NousResearch Hermes 4 ChatML sampling defaults when the caller has
    not explicitly set temperature / top_p / top_k / max_tokens.
    """
    messages = request_payload.get("messages") or []
    if not messages:
        return 400, {
            "error": {
                "message": "At least one message is required.",
                "type": "invalid_request_error",
            }
        }

    upstream: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
    }

    # Apply Hermes 4 ChatML defaults; honour explicit caller overrides
    upstream["temperature"] = request_payload.get("temperature", HERMES_DEFAULT_TEMPERATURE)
    upstream["top_p"] = request_payload.get("top_p", HERMES_DEFAULT_TOP_P)
    upstream["max_tokens"] = request_payload.get("max_tokens", HERMES_DEFAULT_MAX_TOKENS)

    # top_k is not part of the standard OpenAI spec but HuggingFace TGI and
    # many vLLM deployments accept it as an extra parameter.
    top_k = request_payload.get("top_k", HERMES_DEFAULT_TOP_K)
    if top_k is not None:
        # Send as extra_body / top_level param; HF TGI accepts top_level
        upstream["top_k"] = top_k

    if "stop" in request_payload:
        upstream["stop"] = request_payload["stop"]

    url = f"{base_url}/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps(upstream).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = {"error": {"message": f"upstream_http_{exc.code}", "type": "upstream_error"}}
        return exc.code, payload if isinstance(payload, dict) else {
            "error": {"message": str(payload), "type": "upstream_error"}
        }
    except Exception as exc:  # noqa: BLE001
        return 502, {
            "error": {
                "message": f"Upstream request failed: {exc}",
                "type": "upstream_error",
            }
        }

    # Pass through the response as-is (it is already OpenAI-shaped)
    if isinstance(body, dict):
        return 200, body
    return 502, {"error": {"message": "Unexpected upstream response format.", "type": "upstream_error"}}


# ---------------------------------------------------------------------------
# OpenAI Codex web-login backend (legacy path)
# ---------------------------------------------------------------------------

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


def _codex_headers(session: dict[str, Any]) -> dict[str, str]:
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


def _codex_web_chat(
    model: str,
    request_payload: dict[str, Any],
) -> tuple[int, dict[str, Any]]:
    """Call the OpenAI Codex web-login responses endpoint."""
    session = get_live_session()
    input_items = _messages_to_input(request_payload.get("messages") or [])
    if not input_items:
        return 400, {
            "error": {
                "message": "At least one message is required.",
                "type": "invalid_request_error",
            }
        }

    upstream_payload: dict[str, Any] = {
        "model": model,
        "input": input_items,
        "store": False,
        "stream": False,
    }
    if "temperature" in request_payload:
        upstream_payload["temperature"] = request_payload.get("temperature")
    if "max_tokens" in request_payload:
        upstream_payload["max_output_tokens"] = request_payload.get("max_tokens")

    req = urllib.request.Request(
        OPENAI_CODEX_RESPONSES_URL,
        data=json.dumps(upstream_payload).encode("utf-8"),
        headers=_codex_headers(session),
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            upstream = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = {"error": {"message": f"upstream_http_{exc.code}", "type": "upstream_error"}}
        return exc.code, payload if isinstance(payload, dict) else {
            "error": {"message": str(payload), "type": "upstream_error"}
        }
    except Exception as exc:  # noqa: BLE001
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_models() -> dict[str, Any]:
    """Return the list of available models for the model picker in the UI."""
    models = []

    # Always advertise the NousResearch Hermes 4 series
    for model_id in NOUSRESEARCH_MODELS:
        models.append(
            {
                "id": model_id,
                "object": "model",
                "owned_by": "nousresearch",
                "description": (
                    "NousResearch Hermes 4 series — ChatML format, "
                    "temperature=0.6, top_p=0.95, top_k=20"
                ),
            }
        )

    # Also expose the shim model if it is not already in the list
    if SHIM_MODEL_NAME and SHIM_MODEL_NAME not in NOUSRESEARCH_MODELS:
        models.append(
            {
                "id": SHIM_MODEL_NAME,
                "object": "model",
                "owned_by": "custom",
            }
        )

    return {"object": "list", "data": models}


def chat_completions(request_payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Route a chat completion request to the appropriate upstream provider."""
    requested_model = request_payload.get("model")
    raw_model = (
        requested_model
        if isinstance(requested_model, str) and requested_model.strip()
        else SHIM_MODEL_NAME
    )
    model = _normalize_model(raw_model)

    provider = _choose_provider(model)

    if provider == "huggingface":
        return _openai_compat_chat(HF_BASE_URL, HUGGINGFACE_API_KEY, model, request_payload)

    if provider == "openai_compat":
        return _openai_compat_chat(OPENAI_BASE_URL, OPENAI_API_KEY, model, request_payload)

    # codex_web — requires active web-login session
    return _codex_web_chat(model, request_payload)
