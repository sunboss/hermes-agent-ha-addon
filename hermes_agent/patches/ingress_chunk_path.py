"""Patch Vite dist chunks and web_server_dashboard.py to support Home Assistant Ingress basePath.

Issues fixed:
1. Ingress iframe runs under sandboxed origin where `navigator.locks` is undefined, causing React to hang.
2. Vite uses `Xt = function(e) { return `/` + e }` to construct dynamic preload/import URLs for chunks & CSS,
   which drops the `/api/hassio_ingress/<token>` prefix and requests `http://<ha-ip>/assets/...` (404 Not Found),
   breaking the ChatPage and xterm terminal.
3. React Router `history.pushState` / `replaceState` stripped trailing slashes when navigating to
   `<token>?profile=default`, which caused Home Assistant Ingress router to return `404: Not Found` on page refresh.
   Injected history proxy ensures trailing slash is always preserved: `<token>/?profile=...`.
"""

from __future__ import annotations
import pathlib
import sys
import glob

def patch():
    # 1. Patch web_server_dashboard.py to inject navigator.locks polyfill & Vite preload listener & history slash guard
    dash_path = pathlib.Path("/opt/hermes/hermes_cli/web_server_dashboard.py")
    if dash_path.exists():
        content = dash_path.read_text(encoding="utf-8")
        if "replaceState" not in content:
            idx1 = content.find('bootstrap_script = (')
            idx2 = content.find('theme_bootstrap = _render_active_theme_bootstrap_css()')
            if idx1 != -1 and idx2 != -1:
                line_start1 = content.rfind('\n', 0, idx1) + 1
                line_start2 = content.rfind('\n', 0, idx2) + 1
                
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
            for attr in ('href=\"/assets/', 'src=\"/assets/', 'href=\"/favicon.ico\"', 'href=\"/fonts/',
                         'href=\"/ds-assets/', 'src=\"/ds-assets/'):
                html = html.replace(attr, attr.replace('\"/', f'\"{prefix}/', 1))
'''
                content = content[:line_start1] + clean_code + content[line_start2:]
                dash_path.write_text(content, encoding="utf-8")
                print("[patch_ingress_chunks] Patched web_server_dashboard.py bootstrap_script & history slash guard!")

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
