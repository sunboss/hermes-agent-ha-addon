#!/usr/bin/env python3
from __future__ import annotations

import ipaddress
import json
import mimetypes
import os
import urllib.error
import urllib.parse
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from auth_bridge import clear_session, complete_login, get_status, refresh_session, start_login
from provider_shim import chat_completions as shim_chat_completions
from provider_shim import list_models as shim_list_models

UI_DIR = Path(os.environ.get("HERMES_UI_DIR", "/opt/hermes-ha-ui"))
PORT = int(os.environ.get("HERMES_UI_PORT", "8099"))
API_BASE = os.environ.get("HERMES_API_UPSTREAM", "http://127.0.0.1:8642")
API_KEY = os.environ.get("API_SERVER_KEY", "")
ALLOWED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("172.30.0.0/16"),
]
LOOPBACK_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
]


class HermesUiHandler(BaseHTTPRequestHandler):
    server_version = "HermesIngressUI/0.4"

    def _remote_allowed(self) -> bool:
        try:
            remote_ip = ipaddress.ip_address(self.client_address[0])
        except ValueError:
            return False
        return any(remote_ip in network for network in ALLOWED_NETWORKS)

    def _loopback_only(self) -> bool:
        try:
            remote_ip = ipaddress.ip_address(self.client_address[0])
        except ValueError:
            return False
        return any(remote_ip in network for network in LOOPBACK_NETWORKS)

    def _send_common_headers(self, status: int, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()

    def _send_json(self, status: int, payload: dict) -> None:
        self._send_common_headers(status, "application/json")
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def _send_html(self, status: int, html: str) -> None:
        self._send_common_headers(status, "text/html; charset=utf-8")
        self.wfile.write(html.encode("utf-8"))

    def _reject_if_needed(self) -> bool:
        if self._remote_allowed():
            return False
        self._send_json(HTTPStatus.FORBIDDEN, {"error": "forbidden"})
        return True

    def _reject_if_not_loopback(self) -> bool:
        if self._loopback_only():
            return False
        self._send_json(HTTPStatus.FORBIDDEN, {"error": "loopback_only"})
        return True

    def _serve_file(self, target: Path) -> None:
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if target.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        elif target.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif target.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        self._send_common_headers(HTTPStatus.OK, content_type)
        self.wfile.write(target.read_bytes())

    def _serve_index(self) -> None:
        self._serve_file(UI_DIR / "index.html")

    def _read_json_body(self) -> dict:
        length = self.headers.get("Content-Length")
        if not length:
            return {}
        body = self.rfile.read(int(length))
        if not body:
            return {}
        payload = json.loads(body.decode("utf-8"))
        return payload if isinstance(payload, dict) else {}

    def _proxy(self, upstream_path: str) -> None:
        upstream_url = f"{API_BASE}{upstream_path}"
        body = None
        length = self.headers.get("Content-Length")
        if length:
            body = self.rfile.read(int(length))

        headers = {"Authorization": f"Bearer {API_KEY}"}
        content_type = self.headers.get("Content-Type")
        if content_type:
            headers["Content-Type"] = content_type

        request = urllib.request.Request(
            upstream_url,
            data=body,
            headers=headers,
            method=self.command,
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                payload = response.read()
                status = response.getcode()
                response_type = response.headers.get("Content-Type", "application/json")
                self._send_common_headers(status, response_type)
                self.wfile.write(payload)
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            response_type = exc.headers.get("Content-Type", "application/json")
            self._send_common_headers(exc.code, response_type)
            self.wfile.write(payload)
        except Exception as exc:  # noqa: BLE001
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})

    def _callback_page(self, ok: bool, message: str) -> str:
        title = "登录成功" if ok else "登录失败"
        tone = "#74f2d4" if ok else "#ff7a7a"
        return f"""<!doctype html>
<html lang=\"zh-CN\">
  <head>
    <meta charset=\"utf-8\">
    <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
    <title>{title}</title>
    <style>
      body {{
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background: linear-gradient(180deg, #070b17 0%, #040711 48%, #02040a 100%);
        color: #eef4fb;
        font-family: "Segoe UI Variable", "Segoe UI", sans-serif;
      }}
      .panel {{
        width: min(92vw, 560px);
        padding: 32px;
        border-radius: 28px;
        border: 1px solid rgba(168, 188, 221, 0.18);
        background: rgba(7, 12, 24, 0.84);
        box-shadow: 0 30px 90px rgba(0, 0, 0, 0.45);
      }}
      .eyebrow {{
        margin: 0 0 12px;
        color: {tone};
        letter-spacing: 0.16em;
        text-transform: uppercase;
        font-size: 0.74rem;
      }}
      h1 {{ margin: 0 0 14px; font-size: 2rem; }}
      p {{ margin: 0; line-height: 1.75; color: #9cabbe; }}
    </style>
  </head>
  <body>
    <section class=\"panel\">
      <p class=\"eyebrow\">Hermes Web Login</p>
      <h1>{title}</h1>
      <p>{message}</p>
    </section>
  </body>
</html>"""

    def do_OPTIONS(self) -> None:  # noqa: N802
        if self.path.startswith("/shim/"):
            if self._reject_if_not_loopback():
                return
        elif self._reject_if_needed():
            return
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Allow", "GET,POST,DELETE,OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        if path.startswith("/shim/"):
            if self._reject_if_not_loopback():
                return
            if path == "/shim/v1/models":
                self._send_json(HTTPStatus.OK, shim_list_models())
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        if self._reject_if_needed():
            return
        if path.startswith("/api/"):
            upstream_path = path[len("/api") :] or "/"
            if parsed.query:
                upstream_path = f"{upstream_path}?{parsed.query}"
            self._proxy(upstream_path)
            return
        if path == "/auth/status":
            self._send_json(HTTPStatus.OK, get_status())
            return
        if path == "/auth/start":
            status, payload = start_login()
            self._send_json(status, payload)
            return
        if path == "/auth/callback":
            query = urllib.parse.parse_qs(parsed.query)
            status, payload = complete_login(
                code=query.get("code", [None])[0],
                state_value=query.get("state", [None])[0],
            )
            if status == HTTPStatus.OK:
                self._send_html(status, self._callback_page(True, "OpenAI 登录已完成。可以回到 Home Assistant 页面继续使用 Hermes。"))
            else:
                self._send_html(status, self._callback_page(False, payload.get("message") or "登录回调处理失败。"))
            return
        if path == "/health":
            self._send_json(HTTPStatus.OK, {"status": "ok"})
            return

        candidate = path.lstrip("/") or "index.html"
        target = (UI_DIR / candidate).resolve()
        try:
            target.relative_to(UI_DIR.resolve())
        except ValueError:
            self._send_common_headers(HTTPStatus.NOT_FOUND, "text/plain; charset=utf-8")
            self.wfile.write(b"Not found")
            return

        if target.is_file():
            self._serve_file(target)
            return

        self._serve_index()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        if path.startswith("/shim/"):
            if self._reject_if_not_loopback():
                return
            if path == "/shim/v1/chat/completions":
                try:
                    payload = self._read_json_body()
                except json.JSONDecodeError:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": {"message": "invalid_json", "type": "invalid_request_error"}})
                    return
                try:
                    status, body = shim_chat_completions(payload)
                except Exception as exc:  # noqa: BLE001
                    self._send_json(HTTPStatus.BAD_GATEWAY, {"error": {"message": str(exc), "type": "shim_error"}})
                    return
                self._send_json(status, body)
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        if self._reject_if_needed():
            return
        if path.startswith("/api/"):
            upstream_path = path[len("/api") :] or "/"
            if parsed.query:
                upstream_path = f"{upstream_path}?{parsed.query}"
            self._proxy(upstream_path)
            return
        if path == "/auth/exchange":
            try:
                payload = self._read_json_body()
            except json.JSONDecodeError:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
                return
            status, body = complete_login(
                callback_url=payload.get("callback_url"),
                code=payload.get("code"),
                state_value=payload.get("state"),
            )
            self._send_json(status, body)
            return
        if path == "/auth/refresh":
            status, body = refresh_session()
            self._send_json(status, body)
            return
        if path == "/auth/logout":
            clear_session()
            self._send_json(HTTPStatus.OK, get_status())
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_DELETE(self) -> None:  # noqa: N802
        if self.path.startswith("/shim/"):
            if self._reject_if_not_loopback():
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        if self._reject_if_needed():
            return
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            upstream_path = path[len("/api") :] or "/"
            if parsed.query:
                upstream_path = f"{upstream_path}?{parsed.query}"
            self._proxy(upstream_path)
            return
        if path == "/auth/logout":
            clear_session()
            self._send_json(HTTPStatus.OK, get_status())
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        print(f"[Hermes UI] {self.address_string()} - {fmt % args}")


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), HermesUiHandler)
    print(f"[Hermes UI] Listening on http://0.0.0.0:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()

