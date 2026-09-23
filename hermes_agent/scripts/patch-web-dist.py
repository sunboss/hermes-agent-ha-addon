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

    # 1. 将所有静态资源转为相对路径（去掉开头的斜杠或./）
    content = content.replace('src="/assets/', 'src="assets/')
    content = content.replace('href="/assets/', 'href="assets/')
    content = content.replace('href="/favicon.ico"', 'href="favicon.ico"')
    content = content.replace('src="./assets/', 'src="assets/')
    content = content.replace('href="./assets/', 'href="assets/')
    content = content.replace('href="./favicon.ico"', 'href="favicon.ico"')

    # 2. 注入动态 <base> 标签 + 锁定 __HERMES_BASE_PATH__
    # 兼容两种 HA 访问模式：
    # 模式A (详情页点开): /api/hassio_ingress/<token>/
    # 模式B (侧边栏点击, iframe顶层): /<slug_hermes_agent>
    ingress_bootstrap = (
        '<script>'
        '(function(){'
        '  var p = window.location.pathname;'
        '  var m1 = p.match(/(\\/api\\/hassio_ingress\\/[^\\/]+)/);'
        '  var m2 = p.match(/(\\/1037d332_hermes_agent)/);'
        '  var ingressPrefix = m1 ? m1[1] : (m2 ? m2[1] : "");'
        '  var base = ingressPrefix ? (ingressPrefix + "/") : "/";'
        '  document.write(\'<base href="\' + base + \'">\');'
        '  try {'
        '    Object.defineProperty(window, "__HERMES_BASE_PATH__", {'
        '      get: function() { return ingressPrefix; },'
        '      set: function(v) { /* prevent upstream overwrite */ },'
        '      configurable: true'
        '    });'
        '  } catch(e) {}'
        '})();'
        '</script>'
    )

    import re
    content = re.sub(r'<script>window\.__HERMES_BASE_PATH__=\(window\.location\.pathname.*?</script>', '', content)

    if '__HERMES_BASE_PATH__' not in content or 'Object.defineProperty' not in content:
        content = content.replace('<head>', f'<head>\n  {ingress_bootstrap}')

    index_path.write_text(content, encoding="utf-8")
    print(f"[patch_web_dist] Successfully injected base & locked __HERMES_BASE_PATH__ in {index_path}")
    return True

if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/hermes/hermes_cli/web_dist/index.html")
    patch_index_html(target)
