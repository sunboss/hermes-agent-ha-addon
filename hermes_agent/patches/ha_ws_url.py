"""Patch upstream Hermes HA platform to use /websocket on the Supervisor proxy.

Background
----------
Upstream ``hermes.gateway.platforms.homeassistant`` (v0.10.0 / v2026.4.16)
builds the HA WebSocket URL by hard-coding::

    ws_url = f"{ws_url}/api/websocket"

That suffix is correct for a direct Home Assistant Core endpoint
(``http://homeassistant.local:8123/api/websocket``) but **wrong** for the
Home Assistant Supervisor proxy that every add-on is routed through: the
Supervisor exposes the HA Core WebSocket at ``ws://supervisor/core/websocket``
— **no** ``/api`` segment.  Without this patch every state-sync reconnect
fails with:

    WARNING gateway.platforms.homeassistant: [Homeassistant] Reconnection
    failed: 502, message='Invalid response status',
    url='ws://supervisor/core/api/websocket'

Upstream v0.10.0 offers no env var or ``config.yaml`` override for the WS
URL path, so we have to patch the installed Python module in place.

What this script does
---------------------
Locates ``hermes/gateway/platforms/homeassistant.py`` inside the Hermes
venv, then replaces the single hard-coded line with a conditional that
preserves backwards compatibility for external HA installs::

    if 'supervisor' in self._hass_url:
        ws_url = f"{ws_url}/websocket"   # HA Supervisor proxy mode
    else:
        ws_url = f"{ws_url}/api/websocket"  # direct HA Core (original)

Idempotent — uses a marker comment to skip re-patching on rebuild.
Non-fatal — logs a warning and exits 0 if the pattern isn't found, so that
upstream refactors don't break the build (they'll just need a new patch).

Run at image build time (Dockerfile), not at container start.
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


def _replacement(match: re.Match[str]) -> str:
    indent = match.group(1)
    return (
        f"{indent}# {MARKER}\n"
        f"{indent}if 'supervisor' in (self._hass_url or ''):\n"
        f"{indent}    ws_url = f\"{{ws_url}}/websocket\"\n"
        f"{indent}else:\n"
        f"{indent}    ws_url = f\"{{ws_url}}/api/websocket\""
    )


def main() -> int:
    try:
        import hermes.gateway.platforms.homeassistant as module  # type: ignore
    except ImportError as exc:
        print(f"[patches.ha_ws_url] cannot import module: {exc}; skipping")
        return 0

    path = pathlib.Path(module.__file__ or "")
    if not path.is_file():
        print(f"[patches.ha_ws_url] module file not found: {path}; skipping")
        return 0

    src = path.read_text(encoding="utf-8")
    if MARKER in src:
        print(f"[patches.ha_ws_url] already applied: {path}")
        return 0

    new_src, count = _PATTERN.subn(_replacement, src, count=1)
    if count == 0:
        print(
            f"[patches.ha_ws_url] WARNING: pattern not found in {path}; "
            f"upstream may have refactored. Skipping."
        )
        return 0

    path.write_text(new_src, encoding="utf-8")
    print(f"[patches.ha_ws_url] applied: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
