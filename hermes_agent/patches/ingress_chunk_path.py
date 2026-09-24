"""Unified Ingress & Dashboard Patch for Hermes Agent HA Add-on.

Consolidates all web_server_dashboard.py and Vite bundle patches in one place:
1. Places `bootstrap_script` at the top of `<head>` so `window.__HERMES_BASE_PATH__` is defined before any ES module executes.
2. Injects `navigator.locks` polyfill for sandboxed Home Assistant Ingress iframes.
3. Injects `history.pushState` / `replaceState` guard to keep trailing slash (`/api/hassio_ingress/<token>/?profile=default`), preventing Ingress 404 on browser reload.
4. Patches Vite's `Xt()` dynamic asset path builder in `react-vendor-*.js` to prepend `window.__HERMES_BASE_PATH__`, resolving 404s on lazy chunks (`ChatPage`) and dynamic CSS (`xterm`).
"""

from __future__ import annotations
import glob
import pathlib
import sys


def patch() -> int:
    # 1. Patch web_server_dashboard.py
    dash_path = pathlib.Path("/opt/hermes/hermes_cli/web_server_dashboard.py")
    if dash_path.exists():
        content = dash_path.read_text(encoding="utf-8")

        # 1a. Move bootstrap_script injection to <head> top
        old_head = 'html = html.replace("</head>", f"{bootstrap_script}</head>", 1)'
        new_head = 'html = html.replace("<head>", f"<head>{bootstrap_script}", 1) if "<head>" in html else html.replace("</head>", f"{bootstrap_script}</head>", 1)'
        if old_head in content:
            content = content.replace(old_head, new_head, 1)

        # 1b. Inject navigator.locks polyfill, vite:preloadError handler & trailing-slash history proxy
        if "replaceState" not in content:
            idx1 = content.find("bootstrap_script = (")
            idx2 = content.find("theme_bootstrap = _render_active_theme_bootstrap_css()")
            if idx1 != -1 and idx2 != -1:
                line_start1 = content.rfind("\n", 0, idx1) + 1
                line_start2 = content.rfind("\n", 0, idx2) + 1

                clean_code = '''        bootstrap_script = (
            f"<script>{token_js}"
            f"window.__HERMES_DASHBOARD_EMBEDDED_CHAT__={chat_js};"
            f'window.__HERMES_BASE_PATH__="{prefix}";'
            f"window.__HERMES_AUTH_REQUIRED__={'true' if gated else 'false'};"
            f"window.__HERMES_INITIAL_PROFILE__={initial_profile_js};"
            f"window.__HERMES_DASHBOARD_PROFILE__={serving_profile_js};"
            f"</script>"
        )
        ingress_shim = (
            "<script>"
            "if(!navigator.locks){navigator.locks={request:function(n,o,c){var fn=typeof o==='function'?o:c;return Promise.resolve(fn?fn({name:n}):null);}};} "
            "window.addEventListener('vite:preloadError',function(e){e.preventDefault();}); "
            "(function(){var b=window.__HERMES_BASE_PATH__;if(b){['pushState','replaceState'].forEach(function(m){var orig=history[m];history[m]=function(s,t,u){if(typeof u==='string'&&(u===b||u.indexOf(b+'?')===0)){u=b+'/'+u.slice(b.length);}return orig.call(this,s,t,u);};});}})(); "
            "</script>"
        )
        bootstrap_script = bootstrap_script + ingress_shim
        if prefix:
            for attr in ('href="/assets/', 'src="/assets/', 'href="/favicon.ico"', 'href="/fonts/',
                         'href="/ds-assets/', 'src="/ds-assets/'):
                html = html.replace(attr, attr.replace('"/', f'"{prefix}/', 1))
'''
                content = content[:line_start1] + clean_code + content[line_start2:]

        dash_path.write_text(content, encoding="utf-8")
        print("[ingress_chunk_path] Patched web_server_dashboard.py successfully.")

    # 2. Patch Vite Xt() helper in react-vendor-*.js
    for fpath in glob.glob("/opt/hermes/hermes_cli/web_dist/assets/react-vendor-*.js"):
        p = pathlib.Path(fpath)
        c = p.read_text(encoding="utf-8")
        old_xt = "Xt=function(e){return`/`+e}"
        new_xt = "Xt=function(e){let b=(typeof window<`u`&&window.__HERMES_BASE_PATH__)||``;return(b?b.replace(/\\/+$/,``):``)+`/`+e.replace(/^\\/+/,``)}"
        if old_xt in c:
            p.write_text(c.replace(old_xt, new_xt, 1), encoding="utf-8")
            print(f"[ingress_chunk_path] Patched Vite Xt() in {p.name}.")

    return 0


if __name__ == "__main__":
    sys.exit(patch())
