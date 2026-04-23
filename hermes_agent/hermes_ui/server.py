#!/usr/bin/env python3
"""
hermes_ui/server.py  —  Hermes Agent HA Add-on: Ingress UI Server
==================================================================
Version: 0.14.0

Single-process HTTP server that runs at HERMES_UI_PORT (default 8099) inside the
Home Assistant Ingress proxy.  It handles seven distinct traffic classes:

  1. Static UI files       — index.html, app.js, styles.css, … (HERMES_UI_DIR)
  2. Hermes API proxy      — /api/**   →  proxied to Hermes gateway (API_BASE :8642)
  3. Auth bridge           — /auth/**  →  local PKCE OAuth helpers (auth_bridge.py)
  4. ttyd proxy            — /ttyd/**  →  HTTP + WebSocket to ttyd (TTYD_PORT :7681)
  5. Panel proxy           — /panel/** →  HTTP + WebSocket to upstream `hermes dashboard`
                                          (PANEL_HOST:PANEL_PORT, default 127.0.0.1:9119)
  6. Provider shim         — /shim/**  →  loopback-only; LLM bridge for web_login mode
  7. Metadata endpoints    — /models, /health, /config-model  →  local; never proxied

Security model
--------------
  - Remote access is restricted to ALLOWED_NETWORKS (127.x, ::1, 172.30.0.0/16).
    172.30.0.0/16 is the Home Assistant Supervisor/Ingress internal subnet.
  - /shim/** is further restricted to LOOPBACK_NETWORKS (127.x, ::1) only, because
    the shim can proxy requests with stored OAuth tokens to upstream LLM providers.
  - API_KEY (from API_SERVER_KEY env var) is forwarded to the Hermes gateway for
    per-request authentication; omitted entirely when the key is blank.

Environment variables
---------------------
  HERMES_UI_DIR        Path to the bundled UI files   (default: /opt/hermes-ha-ui)
  HERMES_UI_PORT       Port this server listens on     (default: 8099)
  HERMES_API_UPSTREAM  Hermes gateway base URL         (default: http://127.0.0.1:8642)
  API_SERVER_KEY       Bearer token for Hermes gateway (default: "")
  HERMES_TTYD_HOST     ttyd bind host                  (default: 127.0.0.1)
  HERMES_TTYD_PORT     ttyd port                       (default: 7681)
  HERMES_PANEL_HOST    hermes dashboard bind host      (default: 127.0.0.1)
  HERMES_PANEL_PORT    hermes dashboard port            (default: 9119)

Adding a new route
------------------
  1. Add handling in do_GET / do_POST (and do_DELETE if needed).
  2. Add the path to the do_HEAD set literal so HEAD pre-flight works.
  3. Add the path to the do_OPTIONS Allow header string if the browser will
     send CORS pre-flight requests to it.
"""
from __future__ import annotations

import ipaddress
import json
import mimetypes
import os
import re
import select
import socket
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
TTYD_HOST = os.environ.get("HERMES_TTYD_HOST", "127.0.0.1")
TTYD_PORT = int(os.environ.get("HERMES_TTYD_PORT", "7681"))
# Upstream `hermes dashboard` web UI (introduced in Hermes v2026.4.13).
# run.sh starts it on 127.0.0.1:9119; this server reverse-proxies /panel/**
# to it so HA Ingress's single-port model can reach it.
PANEL_HOST = os.environ.get("HERMES_PANEL_HOST", "127.0.0.1")
PANEL_PORT = int(os.environ.get("HERMES_PANEL_PORT", "9119"))
ALLOWED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("172.30.0.0/16"),
]
LOOPBACK_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
]
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}
TTYD_ROOT_PATHS: set[str] = set()


class HermesUiHandler(BaseHTTPRequestHandler):
    server_version = "HermesIngressUI/0.9"

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
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(data)

    def _send_html(self, status: int, html: str) -> None:
        data = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(data)

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
        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(data)

    def _serve_index(self) -> None:
        addon_version = os.environ.get("ADDON_VERSION", "unknown")
        hermes_upstream = os.environ.get("HERMES_UPSTREAM_LABEL", "upstream")
        index_path = UI_DIR / "index.html"
        html = index_path.read_text(encoding="utf-8")
        html = html.replace("{{ADDON_VERSION}}", f"v{addon_version}")
        html = html.replace("{{HERMES_UPSTREAM}}", hermes_upstream)
        data = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self) -> dict:
        length = self.headers.get("Content-Length")
        if not length:
            return {}
        body = self.rfile.read(int(length))
        if not body:
            return {}
        payload = json.loads(body.decode("utf-8"))
        return payload if isinstance(payload, dict) else {}

    def _proxy_api(self, upstream_path: str) -> None:
        """Proxy a request to the Hermes gateway at API_BASE.

        Retries up to _PROXY_RETRIES times on ConnectionRefusedError / OSError so that
        transient startup race-conditions (UI is up but gateway is still initialising)
        are handled gracefully instead of surfacing a raw Python exception string.
        """
        import errno as _errno
        import time as _time

        upstream_url = f"{API_BASE}{upstream_path}"
        body = None
        length = self.headers.get("Content-Length")
        if length:
            body = self.rfile.read(int(length))

        headers = {}
        if API_KEY:
            headers["Authorization"] = f"Bearer {API_KEY}"
        content_type = self.headers.get("Content-Type")
        if content_type:
            headers["Content-Type"] = content_type

        request = urllib.request.Request(
            upstream_url,
            data=body,
            headers=headers,
            method=self.command,
        )

        _PROXY_RETRIES = 3
        _RETRY_DELAY = 1.5  # seconds between retries

        for attempt in range(_PROXY_RETRIES):
            try:
                with urllib.request.urlopen(request, timeout=180) as response:
                    payload = response.read()
                    status = response.getcode()
                    response_type = response.headers.get("Content-Type", "application/json")
                    self._send_common_headers(status, response_type)
                    self.wfile.write(payload)
                return  # success — done
            except urllib.error.HTTPError as exc:
                payload = exc.read()
                response_type = exc.headers.get("Content-Type", "application/json")
                self._send_common_headers(exc.code, response_type)
                self.wfile.write(payload)
                return
            except (BrokenPipeError, ConnectionResetError):
                return
            except OSError as exc:
                # ConnectionRefusedError is a subclass of OSError (errno 111).
                # Retry if the gateway is not yet accepting connections.
                is_refused = getattr(exc, "errno", None) in (
                    _errno.ECONNREFUSED,
                    _errno.ENOENT,  # Unix socket not yet created
                )
                if is_refused and attempt < _PROXY_RETRIES - 1:
                    _time.sleep(_RETRY_DELAY)
                    continue
                # Final attempt failed or non-retryable OSError — return friendly 503
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {
                        "error": "gateway_unavailable",
                        "message": "Hermes gateway is temporarily unavailable. Please try again in a few seconds.",
                    },
                )
                return
            except Exception as exc:  # noqa: BLE001
                self._send_json(
                    HTTPStatus.BAD_GATEWAY,
                    {
                        "error": "proxy_error",
                        "message": f"代理请求失败：{type(exc).__name__}",
                    },
                )
                return

    # JavaScript injected into ttyd's HTML page.
    #
    # Root cause of 502:
    #   ttyd JS makes TWO requests that both use absolute URLs based on
    #   window.location.HOST (bypassing HA Ingress token path):
    #
    #   1. fetch('http://HOST:8123/ttyd/token')   ← GET one-time auth token
    #   2. new WebSocket('ws://HOST:8123/ttyd/ws?token=XXX')  ← connect terminal
    #
    #   Both bypass HA Ingress → HA returns 502 or 404.
    #   Without a valid token from step 1, step 2 also fails even if URL is fixed.
    #
    # Fix: intercept both fetch() and WebSocket() in the browser:
    #   1. Redirect /ttyd/token fetches to a relative path (./token) so they
    #      travel through HA Ingress → our server → ttyd.
    #   2. Rewrite WebSocket URL to include the full HA Ingress path AND preserve
    #      the ?token= query parameter.
    _TTYD_WS_PATCH = (
        "<script>"
        "(function(){"
        # --- patch fetch() for token endpoint ---
        "var _f=window.fetch;"
        "window.fetch=function(url,opts){"
        "if(typeof url==='string'&&(url.indexOf('/ttyd/token')!==-1)){"
        # rewrite absolute /ttyd/token to relative ./token
        "url='./token';}"
        "return _f.call(this,url,opts);};"
        # --- patch XMLHttpRequest for token endpoint ---
        "var _XHR=window.XMLHttpRequest;"
        "if(_XHR){"
        "var _open=_XHR.prototype.open;"
        "_XHR.prototype.open=function(m,url){"
        "if(typeof url==='string'&&url.indexOf('/ttyd/token')!==-1)url='./token';"
        "return _open.apply(this,arguments);};"
        "}"
        # --- patch WebSocket() to fix URL + preserve query string ---
        "var _WS=window.WebSocket;"
        "window.WebSocket=function(url,p){"
        "if(typeof url==='string'&&(url.startsWith('ws://')||url.startsWith('wss://'))){"
        "try{"
        "var u=new URL(url);"
        "if(u.pathname.endsWith('/ws')){"
        # build new URL: current page path (contains ingress token) + /ws + original ?token=
        "var base=window.location.pathname.replace(/\\/+$/,'')+'/ws';"
        "url=(window.location.protocol==='https:'?'wss://':'ws://')"
        "+window.location.host+base+u.search;"  # u.search = '?token=XXX'
        "}"
        "}catch(e){}}"
        "return p?new _WS(url,p):new _WS(url);};"
        "window.WebSocket.prototype=_WS.prototype;"
        "['CONNECTING','OPEN','CLOSING','CLOSED'].forEach(function(k){window.WebSocket[k]=_WS[k];});"
        "})();"
        "</script>"
    )

    def _proxy_ttyd_http(self) -> None:
        upstream_url = f"http://{TTYD_HOST}:{TTYD_PORT}{self.path}"
        body = None
        length = self.headers.get("Content-Length")
        if length:
            body = self.rfile.read(int(length))

        headers = {}
        for key, value in self.headers.items():
            lower = key.lower()
            if lower in HOP_BY_HOP_HEADERS or lower == "host":
                continue
            # CRITICAL: strip Accept-Encoding so ttyd never returns gzip.
            # urllib does not auto-decompress, and we need to inject the
            # JS patch into the HTML payload — impossible on a gzip stream.
            # If we forwarded a gzip body and kept Content-Encoding: gzip,
            # HA Supervisor's aiohttp proxy would later fail with
            # ContentDecodingError → the browser would see a 502.  See
            # v0.9.8 fix in CHANGELOG.md.
            if lower == "accept-encoding":
                continue
            headers[key] = value
        headers["Host"] = f"{TTYD_HOST}:{TTYD_PORT}"
        headers["Accept-Encoding"] = "identity"

        request = urllib.request.Request(
            upstream_url,
            data=body,
            headers=headers,
            method=self.command,
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = response.read()
                content_type = response.headers.get("Content-Type", "")
                # Inject WebSocket URL patch into ttyd's HTML so the browser
                # uses the full HA Ingress path instead of the bare /ttyd/ws path.
                if "text/html" in content_type:
                    patch = self._TTYD_WS_PATCH.encode()
                    payload = payload.replace(b"</head>", patch + b"</head>", 1)
                    if patch not in payload:  # no </head> tag — prepend
                        payload = patch + payload
                self.send_response(response.getcode())
                seen: set[str] = set()
                for key, value in response.headers.items():
                    lower = key.lower()
                    if lower in HOP_BY_HOP_HEADERS or lower == "cache-control":
                        continue
                    # Skip content-length — we'll set the correct value below
                    if lower == "content-length":
                        continue
                    # Strip any content-encoding header the upstream sent —
                    # we forced Accept-Encoding: identity above so the body
                    # is guaranteed to be uncompressed plain text/html.
                    if lower == "content-encoding":
                        continue
                    if lower not in seen:
                        self.send_header(key, value)
                        seen.add(lower)
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(payload)
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            self.send_response(exc.code)
            seen2: set[str] = set()
            for key, value in exc.headers.items():
                lower = key.lower()
                if lower in HOP_BY_HOP_HEADERS or lower == "cache-control":
                    continue
                if lower == "content-length":
                    continue
                if lower not in seen2:
                    self.send_header(key, value)
                    seen2.add(lower)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as exc:  # noqa: BLE001
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})

    def _proxy_ttyd_websocket(self) -> None:
        """Proxy a WebSocket upgrade request to ttyd.

        Phase 1 (before 101): connect to ttyd and forward the upgrade handshake.
                               Any failure here sends a plain HTTP 502 response.
        Phase 2 (after  101): bidirectional raw-byte relay until either side closes.
                               Errors here just close the connection silently.
        """
        # ---- Phase 1: connect to ttyd ----------------------------------------
        try:
            upstream = socket.create_connection((TTYD_HOST, TTYD_PORT), timeout=10)
        except OSError as exc:
            self.log_error("[ttyd-ws] cannot connect to ttyd:%s — %s", TTYD_PORT, exc)
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": f"ttyd unavailable: {exc}"})
            return

        try:
            # Build upgrade request for ttyd — replace Host, keep all WS headers
            request_lines = [f"{self.command} {self.path} HTTP/1.1"]
            has_host = False
            for key, value in self.headers.items():
                lower = key.lower()
                if lower == "host":
                    request_lines.append(f"Host: {TTYD_HOST}:{TTYD_PORT}")
                    has_host = True
                elif lower in HOP_BY_HOP_HEADERS and lower not in {
                    "connection", "upgrade", "sec-websocket-key",
                    "sec-websocket-version", "sec-websocket-extensions",
                    "sec-websocket-protocol",
                }:
                    # Strip generic hop-by-hop but KEEP WebSocket-specific ones
                    continue
                else:
                    request_lines.append(f"{key}: {value}")
            if not has_host:
                request_lines.append(f"Host: {TTYD_HOST}:{TTYD_PORT}")
            request_lines += ["", ""]
            upstream.sendall("\r\n".join(request_lines).encode())

            # Read ttyd's 101 response
            response = bytearray()
            while b"\r\n\r\n" not in response:
                chunk = upstream.recv(4096)
                if not chunk:
                    raise ConnectionError("ttyd closed during WebSocket handshake")
                response.extend(chunk)

            # Check ttyd accepted the upgrade
            first_line = response.split(b"\r\n", 1)[0]
            if b"101" not in first_line:
                self.log_error("[ttyd-ws] ttyd rejected upgrade: %s", first_line)
                self._send_json(HTTPStatus.BAD_GATEWAY,
                                {"error": f"ttyd rejected upgrade: {first_line.decode(errors='replace')}"})
                upstream.close()
                return

            self.log_message("[ttyd-ws] WebSocket tunnel open — %s", self.path)

        except Exception as exc:  # noqa: BLE001
            self.log_error("[ttyd-ws] handshake failed: %s", exc)
            try:
                self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})
            except Exception:
                pass
            upstream.close()
            return

        # ---- Phase 2: relay bytes until either side closes -------------------
        # Forward ttyd's 101 response to the client, then relay raw bytes.
        self.close_connection = True
        upstream.settimeout(None)
        self.connection.settimeout(None)
        try:
            self.connection.sendall(bytes(response))
            sockets = [self.connection, upstream]
            while True:
                readable, _, _ = select.select(sockets, [], [], 60)
                if not readable:
                    # keepalive ping — nothing to do; loop
                    continue
                for sock in readable:
                    try:
                        chunk = sock.recv(65536)
                    except OSError:
                        chunk = b""
                    if not chunk:
                        return  # one side closed → stop relay
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

    # -----------------------------------------------------------------------
    # /panel/** reverse proxy  →  upstream `hermes dashboard` FastAPI SPA
    # -----------------------------------------------------------------------
    # Upstream layout: `hermes dashboard` binds to 127.0.0.1:9119 and serves a
    # Vite-built single-page app with absolute-path asset references (e.g.
    # `<script src="/assets/index-xyz.js">`) plus runtime fetch() / WebSocket
    # calls to absolute paths like `/api/session/list`.  None of those paths
    # know about Home Assistant Ingress — they'd bypass the ingress token and
    # 404 straight at HA's nginx.
    #
    # Fix (three parts):
    #   1. HTTP path stripping: incoming "/panel/foo" → upstream "/foo".
    #   2. HTML rewrite: for text/html responses, rewrite `href="/x"` /
    #      `src="/x"` / `action="/x"` to `./x` so the browser resolves them
    #      against the current page (which sits under /panel/).
    #   3. JS patch: inject a <script> that wraps fetch / XMLHttpRequest /
    #      WebSocket.  Any absolute-path URL that isn't already under the
    #      panel base gets the panel base prepended.  This catches the
    #      runtime API calls that HTML rewriting can't touch.
    _PANEL_JS_PATCH = (
        "<script>"
        "(function(){"
        "var p=window.location.pathname;"
        "var i=p.indexOf('/panel');"
        "var BASE=i>=0?p.slice(0,i+6):'/panel';"
        "function rewrite(u){"
        "if(typeof u!=='string')return u;"
        "if(u.length===0)return u;"
        "if(u.charAt(0)==='/'&&u.charAt(1)!=='/'){"
        "if(u.indexOf(BASE+'/')===0||u===BASE)return u;"
        "return BASE+u;"
        "}"
        "return u;"
        "}"
        "function rewriteWs(u){"
        "if(typeof u!=='string')return u;"
        "if(u.indexOf('ws://')!==0&&u.indexOf('wss://')!==0)return u;"
        "try{"
        "var parsed=new URL(u);"
        "if(parsed.pathname.indexOf(BASE+'/')===0||parsed.pathname===BASE)return u;"
        "var scheme=(window.location.protocol==='https:'?'wss://':'ws://');"
        "return scheme+window.location.host+BASE+parsed.pathname+parsed.search;"
        "}catch(e){return u;}"
        "}"
        "var _f=window.fetch;"
        "if(_f){"
        "window.fetch=function(input,opts){"
        "if(typeof input==='string'){input=rewrite(input);}"
        "else if(input&&typeof input.url==='string'&&input.url.charAt(0)==='/'){"
        "try{input=new Request(rewrite(input.url),input);}catch(e){}"
        "}"
        "return _f.call(this,input,opts);"
        "};"
        "}"
        "var _XHR=window.XMLHttpRequest;"
        "if(_XHR&&_XHR.prototype&&_XHR.prototype.open){"
        "var _open=_XHR.prototype.open;"
        "_XHR.prototype.open=function(m,url){"
        "arguments[1]=rewrite(url);"
        "return _open.apply(this,arguments);"
        "};"
        "}"
        "var _WS=window.WebSocket;"
        "if(_WS){"
        "var WSProxy=function(url,protocols){"
        "url=rewriteWs(url);"
        "return protocols?new _WS(url,protocols):new _WS(url);"
        "};"
        "WSProxy.prototype=_WS.prototype;"
        "['CONNECTING','OPEN','CLOSING','CLOSED'].forEach(function(k){WSProxy[k]=_WS[k];});"
        "window.WebSocket=WSProxy;"
        "}"
        "})();"
        "</script>"
    )

    # Rewrites absolute-path attribute values in HTML so the browser resolves
    # them against the current (HA-ingress-prefixed) page path, not the bare
    # origin.  Only touches values that start with a single "/" — not "//host"
    # (protocol-relative), not "http://", not "#anchor".
    _PANEL_HTML_ATTR_RX = re.compile(
        rb'(\s(?:href|src|action|data-src|data-href)\s*=\s*)(["\'])/(?!/)',
        re.IGNORECASE,
    )

    def _rewrite_panel_html(self, body: bytes) -> bytes:
        # Replace every /foo with ./foo so relative resolution walks up from
        # the current /panel/... page to the right absolute path.
        body = self._PANEL_HTML_ATTR_RX.sub(lambda m: m.group(1) + m.group(2) + b"./", body)
        # Inject the runtime JS patch as early as possible in <head>.
        patch = self._PANEL_JS_PATCH.encode()
        if b"<head>" in body:
            body = body.replace(b"<head>", b"<head>" + patch, 1)
        elif b"</head>" in body:
            body = body.replace(b"</head>", patch + b"</head>", 1)
        else:
            body = patch + body
        return body

    # Friendly "still building..." fallback page.  Auto-refreshes every 5s via
    # <meta refresh> so the user doesn't have to manually reload once Vite
    # finishes compiling the SPA.  Only served when the underlying GET to
    # hermes dashboard refuses the connection (ECONNREFUSED) or the upstream
    # returns 502 / 503 while still booting.
    _PANEL_BOOT_PAGE = (
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta http-equiv="refresh" content="4">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Hermes 面板正在构建...</title>'
        '<style>'
        'body{margin:0;min-height:100vh;display:grid;place-items:center;'
        'background:linear-gradient(180deg,#070b17 0%,#040711 48%,#02040a 100%);'
        'color:#eef4fb;font-family:"Segoe UI Variable","Segoe UI",sans-serif;}'
        '.panel{width:min(92vw,560px);padding:32px;border-radius:28px;'
        'border:1px solid rgba(168,188,221,.18);background:rgba(7,12,24,.84);'
        'box-shadow:0 30px 90px rgba(0,0,0,.45);}'
        '.eyebrow{margin:0 0 12px;color:#74f2d4;letter-spacing:.16em;'
        'text-transform:uppercase;font-size:.74rem;}'
        'h1{margin:0 0 14px;font-size:1.8rem;}'
        'p{margin:0 0 10px;line-height:1.75;color:#9cabbe;}'
        '.dot{display:inline-block;width:8px;height:8px;border-radius:999px;'
        'background:#74f2d4;box-shadow:0 0 12px #74f2d4;animation:p 1.2s ease-in-out infinite;}'
        '@keyframes p{0%,100%{opacity:.35}50%{opacity:1}}'
        '</style></head><body><section class="panel">'
        '<p class="eyebrow"><span class="dot"></span> Hermes Dashboard</p>'
        '<h1>官方控制面板正在构建…</h1>'
        '<p>首次访问此页时，<code>hermes dashboard</code> 需要先构建 Web 资源，大约需要 30–60 秒。</p>'
        '<p>这个页面会每 4 秒自动刷新一次，构建完成后会直接进入控制面板。</p>'
        '</section></body></html>'
    )

    def _proxy_panel_http(self) -> None:
        import errno as _errno
        import time as _time

        parsed = urllib.parse.urlsplit(self.path)
        upstream_path = parsed.path[len("/panel"):] or "/"
        if parsed.query:
            upstream_path = f"{upstream_path}?{parsed.query}"
        upstream_url = f"http://{PANEL_HOST}:{PANEL_PORT}{upstream_path}"

        body = None
        length = self.headers.get("Content-Length")
        if length:
            body = self.rfile.read(int(length))

        headers: dict[str, str] = {}
        for key, value in self.headers.items():
            lower = key.lower()
            if lower in HOP_BY_HOP_HEADERS or lower == "host":
                continue
            # Force identity encoding — we need plaintext HTML to inject the patch.
            if lower == "accept-encoding":
                continue
            headers[key] = value
        headers["Host"] = f"{PANEL_HOST}:{PANEL_PORT}"
        headers["Accept-Encoding"] = "identity"

        request = urllib.request.Request(
            upstream_url,
            data=body,
            headers=headers,
            method=self.command,
        )

        # Boot-window retry: `hermes dashboard` starts listening on 9119
        # AFTER its Vite build finishes (~30–60s on first boot).  During that
        # window GETs refuse with ECONNREFUSED.  Short in-proxy retry papers
        # over the momentary case; sustained failure falls through to the
        # friendly auto-refreshing HTML page below (only for HTML-accepting
        # browser GETs — SPA asset/API fetches still get JSON 502 so they
        # can fail fast and the SPA can retry on its own).
        _PANEL_RETRIES = 3
        _PANEL_DELAY = 0.7

        for attempt in range(_PANEL_RETRIES):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    payload = response.read()
                    content_type = response.headers.get("Content-Type", "")
                    if "text/html" in content_type:
                        payload = self._rewrite_panel_html(payload)
                    self.send_response(response.getcode())
                    seen: set[str] = set()
                    for key, value in response.headers.items():
                        lower = key.lower()
                        if lower in HOP_BY_HOP_HEADERS or lower == "cache-control":
                            continue
                        if lower == "content-length":
                            continue
                        if lower == "content-encoding":
                            continue
                        # Strip Location-rewriting for now — upstream should
                        # only redirect with relative paths inside its SPA.
                        if lower not in seen:
                            self.send_header(key, value)
                            seen.add(lower)
                    self.send_header("Content-Length", str(len(payload)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(payload)
                return  # success
            except urllib.error.HTTPError as exc:
                payload = exc.read()
                self.send_response(exc.code)
                seen2: set[str] = set()
                for key, value in exc.headers.items():
                    lower = key.lower()
                    if lower in HOP_BY_HOP_HEADERS or lower == "cache-control":
                        continue
                    if lower == "content-length":
                        continue
                    if lower not in seen2:
                        self.send_header(key, value)
                        seen2.add(lower)
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(payload)
                return
            except (BrokenPipeError, ConnectionResetError):
                return
            except OSError as exc:
                is_refused = getattr(exc, "errno", None) in (
                    _errno.ECONNREFUSED,
                    _errno.ENOENT,
                )
                if is_refused and attempt < _PANEL_RETRIES - 1:
                    _time.sleep(_PANEL_DELAY)
                    continue
                # Final attempt failed — serve the boot page to HTML-accepting
                # browser GETs and JSON 502 to everything else (XHR/SPA/etc).
                accept = (self.headers.get("Accept") or "").lower()
                wants_html = (
                    self.command == "GET"
                    and ("text/html" in accept or "*/*" in accept or not accept)
                    and upstream_path.rstrip("?").split("?", 1)[0].endswith(("/", ".html"))
                )
                if is_refused and wants_html:
                    data = self._PANEL_BOOT_PAGE.encode("utf-8")
                    self.send_response(HTTPStatus.SERVICE_UNAVAILABLE)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Retry-After", "4")
                    self.end_headers()
                    self.wfile.write(data)
                    return
                self._send_json(
                    HTTPStatus.BAD_GATEWAY,
                    {
                        "error": "panel_unavailable",
                        "message": (
                            f"Hermes 面板暂时无法连接（{PANEL_HOST}:{PANEL_PORT}）。"
                            "请确认 `hermes dashboard` 子命令在当前 Hermes 版本中可用。"
                        ),
                        "detail": str(exc),
                    },
                )
                return
            except Exception as exc:  # noqa: BLE001
                self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})
                return

    def _proxy_panel_websocket(self) -> None:
        """Proxy a WebSocket upgrade from /panel/** to the upstream dashboard."""
        try:
            upstream = socket.create_connection((PANEL_HOST, PANEL_PORT), timeout=10)
        except OSError as exc:
            self.log_error("[panel-ws] cannot connect to panel:%s — %s", PANEL_PORT, exc)
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": f"panel unavailable: {exc}"})
            return

        try:
            parsed = urllib.parse.urlsplit(self.path)
            upstream_path = parsed.path[len("/panel"):] or "/"
            if parsed.query:
                upstream_path = f"{upstream_path}?{parsed.query}"
            request_lines = [f"{self.command} {upstream_path} HTTP/1.1"]
            has_host = False
            for key, value in self.headers.items():
                lower = key.lower()
                if lower == "host":
                    request_lines.append(f"Host: {PANEL_HOST}:{PANEL_PORT}")
                    has_host = True
                elif lower in HOP_BY_HOP_HEADERS and lower not in {
                    "connection", "upgrade", "sec-websocket-key",
                    "sec-websocket-version", "sec-websocket-extensions",
                    "sec-websocket-protocol",
                }:
                    continue
                else:
                    request_lines.append(f"{key}: {value}")
            if not has_host:
                request_lines.append(f"Host: {PANEL_HOST}:{PANEL_PORT}")
            request_lines += ["", ""]
            upstream.sendall("\r\n".join(request_lines).encode())

            response = bytearray()
            while b"\r\n\r\n" not in response:
                chunk = upstream.recv(4096)
                if not chunk:
                    raise ConnectionError("panel closed during WebSocket handshake")
                response.extend(chunk)

            first_line = response.split(b"\r\n", 1)[0]
            if b"101" not in first_line:
                self.log_error("[panel-ws] panel rejected upgrade: %s", first_line)
                self._send_json(
                    HTTPStatus.BAD_GATEWAY,
                    {"error": f"panel rejected upgrade: {first_line.decode(errors='replace')}"},
                )
                upstream.close()
                return

            self.log_message("[panel-ws] WebSocket tunnel open — %s", self.path)

        except Exception as exc:  # noqa: BLE001
            self.log_error("[panel-ws] handshake failed: %s", exc)
            try:
                self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})
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

    def _is_panel_request(self, path: str) -> bool:
        return path == "/panel" or path.startswith("/panel/")

    def _is_websocket_upgrade(self) -> bool:
        connection = self.headers.get("Connection", "")
        upgrade = self.headers.get("Upgrade", "")
        return "upgrade" in connection.lower() and upgrade.lower() == "websocket"

    def _is_ttyd_request(self, path: str) -> bool:
        return path.startswith("/ttyd") or path in TTYD_ROOT_PATHS

    def _callback_page(self, ok: bool, message: str) -> str:
        title = "\u767b\u5f55\u6210\u529f" if ok else "\u767b\u5f55\u5931\u8d25"
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
        self.send_header("Allow", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
        self.end_headers()

    def do_HEAD(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        if path.startswith("/shim/"):
            if self._reject_if_not_loopback():
                return
            self._send_common_headers(HTTPStatus.OK, "application/json")
            return
        if self._reject_if_needed():
            return
        if self._is_ttyd_request(path):
            self._send_common_headers(HTTPStatus.OK, "text/html; charset=utf-8")
            return
        if self._is_panel_request(path):
            self._send_common_headers(HTTPStatus.OK, "text/html; charset=utf-8")
            return
        if path.startswith("/api/"):
            self._send_common_headers(HTTPStatus.OK, "application/json")
            return
        if path in {"/auth/status", "/auth/start", "/auth/callback", "/health", "/models", "/config-model"}:
            self._send_common_headers(HTTPStatus.OK, "application/json")
            return

        candidate = path.lstrip("/") or "index.html"
        target = (UI_DIR / candidate).resolve()
        try:
            target.relative_to(UI_DIR.resolve())
        except ValueError:
            self._send_common_headers(HTTPStatus.NOT_FOUND, "text/plain; charset=utf-8")
            return

        if target.is_file():
            content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if target.suffix == ".js":
                content_type = "application/javascript; charset=utf-8"
            elif target.suffix == ".css":
                content_type = "text/css; charset=utf-8"
            elif target.suffix == ".html":
                content_type = "text/html; charset=utf-8"
            self._send_common_headers(HTTPStatus.OK, content_type)
            return

        self._send_common_headers(HTTPStatus.OK, "text/html; charset=utf-8")

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
        if self._is_ttyd_request(path):
            if self._is_websocket_upgrade():
                # _proxy_ttyd_websocket handles all its own errors internally
                self._proxy_ttyd_websocket()
            else:
                try:
                    self._proxy_ttyd_http()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                except Exception as exc:  # noqa: BLE001
                    self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})
            return
        if self._is_panel_request(path):
            if self._is_websocket_upgrade():
                self._proxy_panel_websocket()
            else:
                try:
                    self._proxy_panel_http()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                except Exception as exc:  # noqa: BLE001
                    self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})
            return
        if path.startswith("/api/"):
            upstream_path = path[len("/api") :] or "/"
            if parsed.query:
                upstream_path = f"{upstream_path}?{parsed.query}"
            self._proxy_api(upstream_path)
            return
        if path == "/models":
            # Proxy to the real Hermes gateway so the UI shows the actual
            # model served by `config.yaml`, not the static shim list.
            # Falls back to the shim list if the gateway is unreachable.
            try:
                _mreq = urllib.request.Request(
                    f"{API_BASE}/v1/models",
                    headers={"Authorization": f"Bearer {API_KEY}"} if API_KEY else {},
                )
                with urllib.request.urlopen(_mreq, timeout=5) as _mresp:
                    self._send_json(HTTPStatus.OK, json.loads(_mresp.read().decode("utf-8")))
            except Exception:  # noqa: BLE001
                self._send_json(HTTPStatus.OK, shim_list_models())
            return
        if path == "/config-model":
            # Return the model/provider declared in HERMES_HOME/config.yaml so`r`n            # the launcher can show the actual configured model.
            try:
                import yaml as _yaml  # local import — yaml is already a dep
                with open(Path(os.environ.get("HERMES_HOME", "/config/.hermes")) / "config.yaml", "r", encoding="utf-8") as _cf:
                    _cfg = _yaml.safe_load(_cf.read()) or {}
                _mc = _cfg.get("model")
                if isinstance(_mc, str):
                    self._send_json(HTTPStatus.OK, {"model": _mc, "provider": ""})
                elif isinstance(_mc, dict):
                    self._send_json(HTTPStatus.OK, {
                        "model": str(_mc.get("default", "")),
                        "provider": str(_mc.get("provider", "")),
                    })
                else:
                    self._send_json(HTTPStatus.OK, {"model": "", "provider": ""})
            except Exception:  # noqa: BLE001
                self._send_json(HTTPStatus.OK, {"model": "", "provider": ""})
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
                self._send_html(status, self._callback_page(True, "OpenAI \u767b\u5f55\u5df2\u5b8c\u6210\u3002\u53ef\u4ee5\u56de\u5230 Home Assistant \u9875\u9762\u7ee7\u7eed\u4f7f\u7528 Hermes\u3002"))
            else:
                self._send_html(status, self._callback_page(False, payload.get("message") or "\u767b\u5f55\u56de\u8c03\u5904\u7406\u5931\u8d25\u3002"))
            return
        if path == "/health":
            # Fast local liveness probe — also pings the Hermes gateway so the UI
            # can distinguish "UI is up" from "gateway is ready".
            gateway_status = "starting"
            try:
                req = urllib.request.Request(
                    f"{API_BASE}/health",
                    headers={"Authorization": f"Bearer {API_KEY}"} if API_KEY else {},
                    method="GET",
                )
                with urllib.request.urlopen(req, timeout=2) as r:
                    if r.getcode() == 200:
                        gateway_status = "ready"
            except Exception:  # noqa: BLE001
                pass
            self._send_json(HTTPStatus.OK, {
                "status": "ok",
                "gateway": gateway_status,
                "ttyd_port": TTYD_PORT,
            })
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
        if self._is_ttyd_request(path):
            try:
                self._proxy_ttyd_http()
            except (BrokenPipeError, ConnectionResetError):
                return
            except Exception as exc:  # noqa: BLE001
                self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})
            return
        if self._is_panel_request(path):
            try:
                self._proxy_panel_http()
            except (BrokenPipeError, ConnectionResetError):
                return
            except Exception as exc:  # noqa: BLE001
                self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})
            return
        if path.startswith("/api/"):
            upstream_path = path[len("/api") :] or "/"
            if parsed.query:
                upstream_path = f"{upstream_path}?{parsed.query}"
            self._proxy_api(upstream_path)
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

    def do_PUT(self) -> None:  # noqa: N802
        self._proxy_panel_or_api("PUT")

    def do_PATCH(self) -> None:  # noqa: N802
        self._proxy_panel_or_api("PATCH")

    def _proxy_panel_or_api(self, method: str) -> None:
        """Handle PUT / PATCH — currently only routed to /panel/** and /api/**.

        FastAPI-based `hermes dashboard` uses REST-style verbs for some of its
        endpoints (creating/updating config, sessions, skills).  We accept the
        same verbs on /api/** too so callers have a uniform surface.
        """
        if self._reject_if_needed():
            return
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        if self._is_panel_request(path):
            try:
                self._proxy_panel_http()
            except (BrokenPipeError, ConnectionResetError):
                return
            except Exception as exc:  # noqa: BLE001
                self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})
            return
        if path.startswith("/api/"):
            upstream_path = path[len("/api") :] or "/"
            if parsed.query:
                upstream_path = f"{upstream_path}?{parsed.query}"
            self._proxy_api(upstream_path)
            return
        self._send_json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed", "method": method})

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
        if self._is_panel_request(path):
            try:
                self._proxy_panel_http()
            except (BrokenPipeError, ConnectionResetError):
                return
            except Exception as exc:  # noqa: BLE001
                self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})
            return
        if path.startswith("/api/"):
            upstream_path = path[len("/api") :] or "/"
            if parsed.query:
                upstream_path = f"{upstream_path}?{parsed.query}"
            self._proxy_api(upstream_path)
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

