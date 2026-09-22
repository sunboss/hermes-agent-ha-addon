#!/usr/bin/env python3
"""
Patch Hermes Web UI index.html to support both Home Assistant Ingress subpath
and direct LAN root path.
"""
import sys
from pathlib import Path

def patch_index_html(index_path: Path):
    if not index_path.exists():
        print(f"[patch_web_dist] File not found: {index_path}", file=sys.stderr)
        return False

    content = index_path.read_text(encoding="utf-8")

    # 1. 将静态资源绝对路径转为相对路径
    content = content.replace('src="/assets/', 'src="./assets/')
    content = content.replace('href="/assets/', 'href="./assets/')
    content = content.replace('href="/favicon.ico"', 'href="./favicon.ico"')

    # 2. 动态自适应 Ingress 子路径作为 BASE_PATH
    dynamic_base = (
        'window.__HERMES_BASE_PATH__='
        '(window.location.pathname.match(/(\\/api\\/hassio_ingress\\/[^\\/]+)/)'
        '?window.location.pathname.match(/(\\/api\\/hassio_ingress\\/[^\\/]+)/)[1]:"");'
    )
    if 'window.__HERMES_BASE_PATH__=""' in content:
        content = content.replace('window.__HERMES_BASE_PATH__=""', dynamic_base)
    elif 'window.__HERMES_BASE_PATH__=' not in content:
        content = content.replace('</head>', f'<script>{dynamic_base}</script></head>')

    index_path.write_text(content, encoding="utf-8")
    print(f"[patch_web_dist] Successfully patched {index_path}")
    return True

if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/hermes/hermes_cli/web_dist/index.html")
    patch_index_html(target)
