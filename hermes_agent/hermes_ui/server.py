#!/usr/bin/env python3
from __future__ import annotations

import ipaddress
import json
import mimetypes
import os
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

UI_DIR = Path(os.environ.get("HERMES_UI_DIR", "/opt/hermes-ha-ui"))
PORT = int(os.environ.get("HERMES_UI_PORT", "8099"))
API_BASE = os.environ.get("HERMES_API_UPSTREAM", "http://127.0.0.1:8642")
API_KEY = os.environ.get("API_SERVER_KEY", "")
ALLOWED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("172.30.0.0/16"),
]


class HermesUiHandler(BaseHTTPRequestHandler):
    server_version = "HermesIngressUI/0.1"

    def _remote_allowed(self) -> bool:
        try:
            remote_ip = ipaddress.ip_address(self.client_address[0])
        except ValueError:
            return False
        return any(remote_ip in network for network in ALLOWED_NETWORKS)

    def _send_common_headers(self, status: int, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()

    def _reject_if_needed(self) -> bool:
        if self._remote_allowed():
            return False
        self._send_common_headers(HTTPStatus.FORBIDDEN, "application/json")
        self.wfile.write(json.dumps({"error": "forbidden"}).encode("utf-8"))
        return True

    def _serve_file(self, target: Path) -> None:
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self._send_common_headers(HTTPStatus.OK, content_type)
        self.wfile.write(target.read_bytes())

    def _serve_index(self) -> None:
        self._serve_file(UI_DIR / "index.html")

    def _proxy(self) -> None:
        upstream_url = f"{API_BASE}{self.path[len('/api'):] or '/'}"
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
            self._send_common_headers(HTTPStatus.BAD_GATEWAY, "application/json")
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def do_OPTIONS(self) -> None:  # noqa: N802
        if self._reject_if_needed():
            return
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Allow", "GET,POST,DELETE,OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if self._reject_if_needed():
            return
        if self.path.startswith("/api/"):
            self._proxy()
            return
        if self.path == "/health":
            self._send_common_headers(HTTPStatus.OK, "application/json")
            self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))
            return

        candidate = self.path.lstrip("/") or "index.html"
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
        if self._reject_if_needed():
            return
        if self.path.startswith("/api/"):
            self._proxy()
            return
        self._send_common_headers(HTTPStatus.NOT_FOUND, "application/json")
        self.wfile.write(json.dumps({"error": "not_found"}).encode("utf-8"))

    def do_DELETE(self) -> None:  # noqa: N802
        if self._reject_if_needed():
            return
        if self.path.startswith("/api/"):
            self._proxy()
            return
        self._send_common_headers(HTTPStatus.NOT_FOUND, "application/json")
        self.wfile.write(json.dumps({"error": "not_found"}).encode("utf-8"))

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        print(f"[Hermes UI] {self.address_string()} - {fmt % args}")


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), HermesUiHandler)
    print(f"[Hermes UI] Listening on http://0.0.0.0:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
