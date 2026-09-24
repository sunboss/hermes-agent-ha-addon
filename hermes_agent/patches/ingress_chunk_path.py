"""Patch Vite dist chunks and web_server_dashboard.py to support Home Assistant Ingress basePath.

Issues fixed:
1. Ingress iframe runs under sandboxed origin where `navigator.locks` is undefined, causing React to hang.
2. Vite uses `Xt = function(e) { return `/` + e }` to construct dynamic preload/import URLs for chunks & CSS,
   which drops the `/api/hassio_ingress/<token>` prefix and requests `http://<ha-ip>/assets/...` (404 Not Found),
   breaking the ChatPage and xterm terminal.
"""

from __future__ import annotations
import pathlib
import sys
import glob

def patch():
    # 1. Patch web_server_dashboard.py to inject navigator.locks polyfill & Vite preload listener
    dash_path = pathlib.Path("/opt/hermes/hermes_cli/web_server_dashboard.py")
    if dash_path.exists():
        content = dash_path.read_text(encoding="utf-8")
        # Ensure navigator.locks polyfill is included in bootstrap_script
        if "if(!navigator.locks)" not in content:
            target_str = 'bootstrap_script = f"""<script>'
            replacement = (
                'bootstrap_script = f"""<script>'
                "if(!navigator.locks){navigator.locks={request:function(n,o,c){var fn=typeof o==='function'?o:c;return Promise.resolve(fn?fn({name:n}):null);}};} "
                "window.addEventListener('vite:preloadError',function(e){e.preventDefault();}); "
            )
            if target_str in content:
                content = content.replace(target_str, replacement, 1)
                dash_path.write_text(content, encoding="utf-8")
                print("[patch_ingress_chunks] Patched web_server_dashboard.py bootstrap_script!")

    # 2. Patch react-vendor chunk to respect window.__HERMES_BASE_PATH__ in Xt() URL generator
    vendor_files = glob.glob("/opt/hermes/hermes_cli/web_dist/assets/react-vendor-*.js")
    for fpath in vendor_files:
        p = pathlib.Path(fpath)
        c = p.read_text(encoding="utf-8")
        old_xt = "Xt=function(e){return`/`+e}"
        new_xt = "Xt=function(e){let b=(typeof window<`u`&&window.__HERMES_BASE_PATH__)||``;return(b?b.replace(/\\/+$/,``):``)+`/`+e.replace(/^\\/+/,``)}"
        if old_xt in c:
            c = c.replace(old_xt, new_xt, 1)
            p.write_text(c, encoding="utf-8")
            print(f"[patch_ingress_chunks] Patched {p.name} Xt() function!")
        elif new_xt in c:
            print(f"[patch_ingress_chunks] {p.name} already patched.")

    return 0

if __name__ == "__main__":
    sys.exit(patch())
