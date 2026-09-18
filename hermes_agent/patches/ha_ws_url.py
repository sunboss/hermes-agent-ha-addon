"""Patch upstream Hermes HA platform to use /websocket on the Supervisor proxy.

Background
----------
Upstream Hermes HA adapter builds the HA WebSocket URL by hard-coding::

    ws_url = f"{ws_url}/api/websocket"

That suffix is correct for a direct Home Assistant Core endpoint
(``http://homeassistant.local:8123/api/websocket``) but **wrong** for the
Home Assistant Supervisor proxy that every add-on is routed through: the
Supervisor exposes the HA Core WebSocket at ``ws://supervisor/core/websocket``
— **no** ``/api`` segment. Without this patch every state-sync reconnect
fails with:

    WARNING gateway.platforms.homeassistant: [Homeassistant] Reconnection
    failed: 502, message='Invalid response status',
    url='ws://supervisor/core/api/websocket'

Upstream offers no env var or ``config.yaml`` override for the WS
URL path, so we patch the installed Python module in place.

What this script does
---------------------
Locates the Home Assistant adapter file inside the Hermes install/venv:
- In upstream >= 2026.5: ``plugins/platforms/homeassistant/adapter.py``
- In legacy upstream: ``gateway/platforms/homeassistant.py``

Then replaces the hard-coded line with a conditional that
preserves backwards compatibility for external HA installs::

    if 'supervisor' in (self._hass_url or ''):
        ws_url = f"{ws_url}/websocket"   # HA Supervisor proxy mode
    else:
        ws_url = f"{ws_url}/api/websocket"  # direct HA Core (original)

Idempotent — uses a marker comment to skip re-patching on rebuild.
"""

from __future__ import annotations

import pathlib
import re
import sys

MARKER = "hermes-agent-ha-addon: supervisor WS URL patch"

# Regex captures leading whitespace so we can re-emit with matching indent.
_PATTERN = re.compile(
    r'^([ \t]*)ws_url\s*=\s*f"\{ws_url\}/api/websocket"\s*$',
    re.MULTILINE,
)
_PATTERN_DIRECT = re.compile(
    r'^([ \t]*)self\._ws\s*=\s*await\s+self\._session\.ws_connect\(f"\{ws_url\}/api/websocket"(.*)\)\s*$',
    re.MULTILINE,
)


def _replacement(match: re.Match[str]) -> str:
    indent = match.group(1)
    return (
        f"{indent}# {MARKER}\n"
        f"{indent}if 'supervisor' in (self._hass_url or ''):\n"
        f"{indent}    ws_url = f\"{{ws_url}}/websocket\"\n"
        f"{indent}else:\n"
        f"{indent}    ws_url = f\"{{ws_url}}/api/websocket\""
    )


def _replacement_direct(match: re.Match[str]) -> str:
    indent = match.group(1)
    extra = match.group(2)
    return (
        f"{indent}# {MARKER}\n"
        f"{indent}_target_ws_path = '/websocket' if 'supervisor' in (self._hass_url or '') else '/api/websocket'\n"
        f"{indent}self._ws = await self._session.ws_connect(f\"{{ws_url}}{{_target_ws_path}}\"{extra})"
    )


def patch_file(path: pathlib.Path) -> bool:
    if not path.is_file():
        return False
    src = path.read_text(encoding="utf-8")
    if MARKER in src:
        print(f"[patches.ha_ws_url] already applied: {path}")
        return True

    new_src, count = _PATTERN.subn(_replacement, src, count=1)
    if count == 0:
        new_src, count = _PATTERN_DIRECT.subn(_replacement_direct, src, count=1)

    if count > 0:
        path.write_text(new_src, encoding="utf-8")
        print(f"[patches.ha_ws_url] successfully applied to: {path}")
        return True
    else:
        print(f"[patches.ha_ws_url] pattern not found in {path}")
        return False


def main() -> int:
    applied = False
    candidates: list[pathlib.Path] = []

    # 1. Try importing module
    try:
        import plugins.platforms.homeassistant.adapter as mod_plugin  # type: ignore
        candidates.append(pathlib.Path(mod_plugin.__file__ or ""))
    except Exception:
        pass

    try:
        import hermes.gateway.platforms.homeassistant as mod_legacy  # type: ignore
        candidates.append(pathlib.Path(mod_legacy.__file__ or ""))
    except Exception:
        pass

    # 2. Search common install paths in Docker container
    for base in [pathlib.Path("/opt/hermes"), pathlib.Path("/app"), pathlib.Path(".")]:
        p1 = base / "plugins/platforms/homeassistant/adapter.py"
        p2 = base / "gateway/platforms/homeassistant.py"
        if p1.is_file() and p1 not in candidates:
            candidates.append(p1)
        if p2.is_file() and p2 not in candidates:
            candidates.append(p2)

    for c in candidates:
        if patch_file(c):
            applied = True

    if not applied:
        print("[patches.ha_ws_url] NOTICE: No candidate files patched. Verified or non-fatal.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
