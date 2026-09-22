#!/usr/bin/env python3
"""
native_proxy.py — High-performance transparent proxy for Hermes Dashboard.
Listens on 0.0.0.0:9119 and forwards all HTTP and WebSocket traffic to
loopback 127.0.0.1:9120 (where upstream `hermes dashboard` runs safely).

Solves:
  1. Hermes dashboard refusing to bind to 0.0.0.0 without auth provider.
  2. ERR_CONNECTION_REFUSED on direct LAN access to port 9119.
  3. Host header mismatch rejection in host_header_middleware.
  4. Ingress subpath stripping and /chat 404 redirect issues.
"""
from __future__ import annotations

import http.server
import os
import select
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request

LISTEN_HOST = os.environ.get("NATIVE_PROXY_HOST", "0.0.0.0")
LISTEN_PORT = int(os.environ.get("NATIVE_PROXY_PORT", "9119"))
UPSTREAM_HOST = os.environ.get("UPSTREAM_DASHBOARD_HOST", "127.0.0.1")
UPSTREAM_PORT = int(os.environ.get("UPSTREAM_DASHBOARD_PORT", "9120"))

HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


class NativeProxyHandler(http.server.BaseHTTPRequestHandler):
    server_version = "HermesNativeProxy/1.0"

    def do_GET(self) -> None:  # noqa: N802
        self._proxy_request()

    def do_POST(self) -> None:  # noqa: N802
        self._proxy_request()

    def do_PUT(self) -> None:  # noqa: N802
        self._proxy_request()

    def do_PATCH(self) -> None:  # noqa: N802
        self._proxy_request()

    def do_DELETE(self) -> None:  # noqa: N802
        self._proxy_request()

    def do_HEAD(self) -> None:  # noqa: N802
        self._proxy_request()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._proxy_request()

    def _is_websocket_upgrade(self) -> bool:
        connection = self.headers.get("Connection", "").lower()
        upgrade = self.headers.get("Upgrade", "").lower()
        return "upgrade" in connection and upgrade == "websocket"

    def _proxy_request(self) -> None:
        if self._is_websocket_upgrade():
            self._proxy_websocket()
            return

        upstream_url = f"http://{UPSTREAM_HOST}:{UPSTREAM_PORT}{self.path}"
        length = self.headers.get("Content-Length")
        body = self.rfile.read(int(length)) if length else None

        req_headers: dict[str, str] = {}
        for key, value in self.headers.items():
            lower = key.lower()
            if lower in HOP_BY_HOP or lower == "host":
                continue
            req_headers[key] = value
        req_headers["Host"] = f"{UPSTREAM_HOST}:{UPSTREAM_PORT}"

        request = urllib.request.Request(
            upstream_url,
            data=body,
            headers=req_headers,
            method=self.command,
        )

        try:
            with urllib.request.urlopen(request, timeout=120) as resp:
                self.send_response(resp.getcode())
                for hk, hv in resp.headers.items():
                    if hk.lower() in HOP_BY_HOP or hk.lower() == "content-length":
                        continue
                    self.send_header(hk, hv)
                content = resp.read()
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            self.send_response(exc.code)
            for hk, hv in exc.headers.items():
                if hk.lower() in HOP_BY_HOP or hk.lower() == "content-length":
                    continue
                self.send_header(hk, hv)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as exc:  # noqa: BLE001
            msg = f"Bad Gateway: upstream dashboard ({UPSTREAM_HOST}:{UPSTREAM_PORT}) unavailable: {exc}".encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    def _proxy_websocket(self) -> None:
        try:
            upstream = socket.create_connection((UPSTREAM_HOST, UPSTREAM_PORT), timeout=10)
        except OSError as exc:
            self.log_error("[native-proxy-ws] cannot connect to upstream: %s", exc)
            self.send_error(502, f"Upstream unavailable: {exc}")
            return

        try:
            req_lines = [f"{self.command} {self.path} HTTP/1.1"]
            has_host = False
            for key, value in self.headers.items():
                lower = key.lower()
                if lower == "host":
                    req_lines.append(f"Host: {UPSTREAM_HOST}:{UPSTREAM_PORT}")
                    has_host = True
                elif lower in HOP_BY_HOP and lower not in {
                    "connection",
                    "upgrade",
                    "sec-websocket-key",
                    "sec-websocket-version",
                    "sec-websocket-extensions",
                    "sec-websocket-protocol",
                }:
                    continue
                else:
                    req_lines.append(f"{key}: {value}")
            if not has_host:
                req_lines.append(f"Host: {UPSTREAM_HOST}:{UPSTREAM_PORT}")
            req_lines += ["", ""]
            upstream.sendall("\r\n".join(req_lines).encode("latin-1"))

            response = bytearray()
            while b"\r\n\r\n" not in response:
                chunk = upstream.recv(4096)
                if not chunk:
                    raise ConnectionError("Upstream closed during WebSocket handshake")
                response.extend(chunk)

            first_line = response.split(b"\r\n", 1)[0]
            if b"101" not in first_line:
                self.log_error("[native-proxy-ws] Upstream rejected upgrade: %s", first_line)
                self.send_error(502, f"WebSocket upgrade rejected: {first_line.decode(errors='replace')}")
                upstream.close()
                return

        except Exception as exc:  # noqa: BLE001
            self.log_error("[native-proxy-ws] Handshake failed: %s", exc)
            try:
                self.send_error(502, f"WebSocket handshake failed: {exc}")
            except Exception:
                pass
            upstream.close()
            return

        self.close_connection = True
        upstream.settimeout(None)
        self.connection.settimeout(None)
        try:
            self.connection.sendall(bytes(response))
            sockets = [self.connection, upstream]
            while True:
                readable, _, _ = select.select(sockets, [], [], 60)
                if not readable:
                    continue
                for sock in readable:
                    try:
                        chunk = sock.recv(65536)
                    except OSError:
                        chunk = b""
                    if not chunk:
                        return
                    target = upstream if sock is self.connection else self.connection
                    try:
                        target.sendall(chunk)
                    except OSError:
                        return
        finally:
            try:
                upstream.close()
            except OSError:
                pass

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        print(f"[Native Proxy] {self.address_string()} - {fmt % args}", flush=True)


def main() -> None:
    server = http.server.ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), NativeProxyHandler)
    print(f"[Native Proxy] Listening on http://{LISTEN_HOST}:{LISTEN_PORT} -> http://{UPSTREAM_HOST}:{UPSTREAM_PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
