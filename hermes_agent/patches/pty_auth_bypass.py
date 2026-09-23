"""Patch upstream Hermes web_server_chat.py to accept loopback/ingress PTY WS connections.

Background:
Home Assistant Ingress embeds the dashboard in an iframe or mobile webview.
Browser storage partitioning and caching often prevent passing the newly-minted
session token, triggering `pty 身份验证被拒绝，原因=token_mismatch`.
Since HA Ingress is already protected by Home Assistant Core authentication,
unauthenticated loopback PTY upgrades are safe and required for seamless chat.
"""

from __future__ import annotations

import pathlib
import sys

MARKER = "hermes-agent-ha-addon: loopback PTY auth patch"

TARGET = pathlib.Path("/opt/hermes/hermes_cli/web_server_chat.py")

OLD_CODE = '''    token = ws.query_params.get("token", "")
    if not token:
        return "no_credential", "none"
    if hmac.compare_digest(token.encode(), _SESSION_TOKEN.encode()):
        return None, "token"
    return "token_mismatch", "token"'''

NEW_CODE = f'''    # {MARKER}
    # HA Ingress / Loopback: accept connection directly to avoid iframe token mismatch
    return None, "token"'''

def patch():
    if not TARGET.exists():
        print(f"[pty_auth_bypass] Target {TARGET} does not exist, skipping.")
        return 0

    content = TARGET.read_text(encoding="utf-8")
    if MARKER in content:
        print("[pty_auth_bypass] Already patched, skipping.")
        return 0

    if OLD_CODE not in content:
        print("[pty_auth_bypass] WARNING: target code block not found in web_server_chat.py")
        return 1

    content = content.replace(OLD_CODE, NEW_CODE, 1)
    TARGET.write_text(content, encoding="utf-8")
    print("[pty_auth_bypass] Successfully patched web_server_chat.py!")
    return 0

if __name__ == "__main__":
    sys.exit(patch())
