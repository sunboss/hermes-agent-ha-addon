"""Patch upstream Hermes web_server_dashboard.py to place bootstrap_script at <head> top.

Background:
In Vite/Rolldown builds, ES modules and preloads execute early. If bootstrap_script
is appended right before </head>, module top-level evaluations (like api.js) read
`window.__HERMES_BASE_PATH__` as undefined, defaulting to "/" and failing Ingress.
Injecting immediately after <head> ensures global config is ready for all scripts.
"""

from __future__ import annotations

import pathlib
import sys

MARKER = "hermes-agent-ha-addon: head bootstrap script patch"

TARGET = pathlib.Path("/opt/hermes/hermes_cli/web_server_dashboard.py")

OLD_CODE = 'html = html.replace("</head>", f"{bootstrap_script}</head>", 1)'
NEW_CODE = f'''# {MARKER}
        html = html.replace("<head>", f"<head>{{bootstrap_script}}", 1) if "<head>" in html else html.replace("</head>", f"{{bootstrap_script}}</head>", 1)'''

def patch():
    if not TARGET.exists():
        print(f"[head_bootstrap_patch] Target {TARGET} does not exist, skipping.")
        return 0

    content = TARGET.read_text(encoding="utf-8")
    if MARKER in content:
        print("[head_bootstrap_patch] Already patched, skipping.")
        return 0

    if OLD_CODE not in content:
        print("[head_bootstrap_patch] WARNING: target code block not found in web_server_dashboard.py")
        return 1

    content = content.replace(OLD_CODE, NEW_CODE, 1)
    TARGET.write_text(content, encoding="utf-8")
    print("[head_bootstrap_patch] Successfully patched web_server_dashboard.py to inject at <head> top!")
    return 0

if __name__ == "__main__":
    sys.exit(patch())
