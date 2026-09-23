#!/usr/bin/env python3
"""
Patch Hermes Web UI index.html to use pure relative paths,
aligning with Home Assistant Ingress standards (same as Node-RED).
"""
import sys
from pathlib import Path
import re

def patch_index_html(index_path: Path):
    if not index_path.exists():
        print(f"[patch_web_dist] File not found: {index_path}", file=sys.stderr)
        return False

    content = index_path.read_text(encoding="utf-8")

    # 1. 彻底清除任何旧的历史注入（包括所有 script 和 base 标签）
    content = re.sub(r'<script>[\s\S]*?</script>\s*', '', content)
    content = re.sub(r'<base\s+href=[\'"][^\'"]*[\'"]\s*/?>\s*', '', content)

    # 2. 将所有静态资源转为纯相对路径（与 Node-RED 一致，去掉开头的斜杠或 ./）
    content = content.replace('src="/assets/', 'src="assets/')
    content = content.replace('href="/assets/', 'href="assets/')
    content = content.replace('href="/favicon.ico"', 'href="favicon.ico"')
    content = content.replace('src="./assets/', 'src="assets/')
    content = content.replace('href="./assets/', 'href="assets/')
    content = content.replace('href="./favicon.ico"', 'href="favicon.ico"')

    index_path.write_text(content, encoding="utf-8")
    print(f"[patch_web_dist] Successfully converted {index_path} to clean relative paths (no document.write, no base tags).")
    return True

if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/hermes/hermes_cli/web_dist/index.html")
    patch_index_html(target)
