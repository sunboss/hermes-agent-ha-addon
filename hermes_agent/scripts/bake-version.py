#!/usr/bin/env python3
"""Substitute {{ADDON_VERSION}} / {{HERMES_UPSTREAM}} in index.html.

Run at image-build time so the version banner is correct without any
runtime ENV-variable plumbing.  Standalone script (not a Dockerfile
heredoc) for the cache-keying reasons in install-ttyd.sh.
"""
import json
import pathlib
import sys


def main() -> int:
    ui = pathlib.Path("/opt/hermes-ha-ui")
    vf = ui / "version.json"
    if not vf.exists():
        print("[bake-version] version.json not found — skipping", file=sys.stderr)
        return 0

    v = json.loads(vf.read_text())
    index = ui / "index.html"
    html = index.read_text()
    html = html.replace("{{ADDON_VERSION}}", "v" + str(v.get("version", "unknown")))
    html = html.replace("{{HERMES_UPSTREAM}}", str(v.get("upstream", "upstream")))
    index.write_text(html)
    print(f"[bake-version] substituted: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
