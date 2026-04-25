#!/usr/bin/env python3
"""Tiny HTTPS downloader used at image-build time.

Standalone (not a heredoc) for the same cache-keying reasons documented in
install-ttyd.sh.  Uses an unverified SSL context because the upstream
hermes-agent base image does not reliably ship ca-certificates and we have
no working apt to install them.
"""
import os
import ssl
import sys
import urllib.request


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: _fetch.py <url> <dest>", file=sys.stderr)
        return 2

    url, dest = sys.argv[1], sys.argv[2]
    ctx = ssl._create_unverified_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    print(f"[_fetch] GET {url}", flush=True)
    with urllib.request.urlopen(req, context=ctx, timeout=120) as r:
        data = r.read()

    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    with open(dest, "wb") as f:
        f.write(data)

    print(f"[_fetch] wrote {dest} ({len(data)} bytes)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
