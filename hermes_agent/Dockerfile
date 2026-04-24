ARG BUILD_VERSION="2026.4.24.7"
# BUILD_FROM is injected by HA Supervisor as --build-arg at build time
# (arch-specific, e.g. linux/arm64 on aarch64 hosts).  The default here
# is used when building outside of HA (e.g. local docker build).
# To upgrade upstream: change the default tag below.
ARG BUILD_FROM="nousresearch/hermes-agent:latest"

FROM ${BUILD_FROM}

ARG BUILD_VERSION
ARG BUILD_ARCH

# Print build context for log verification.
RUN printf '[Dockerfile] BUILD_FROM=%s  BUILD_ARCH=%s  HOST_ARCH=%s\n' \
      "${BUILD_FROM}" "${BUILD_ARCH}" "$(uname -m)"

ENV HERMES_INSTALL_DIR=/opt/hermes
ENV HERMES_STATE_ROOT=/config
ENV HERMES_HOME=/config/.hermes
ENV HOME=/config
ENV PATH=/opt/hermes/.venv/bin:$PATH
ENV HERMES_UI_PORT=8099
ENV HERMES_UI_DIR=/opt/hermes-ha-ui
ENV HERMES_TTYD_PORT=7681
ENV HERMES_PANEL_HOST=127.0.0.1
ENV HERMES_PANEL_PORT=9119

LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="aarch64|amd64"

RUN set -eux; \
    # Install ttyd binary from GitHub Releases — arch-aware, no Debian sid needed.
    # Debian sid's ttyd is amd64-only and fails on arm64 with exit code 2.
    case "$(uname -m)" in \
      aarch64|arm64) TTYD_ARCH="aarch64" ;; \
      x86_64|amd64)  TTYD_ARCH="x86_64"  ;; \
      *)             echo "[Dockerfile] Unsupported arch: $(uname -m)" >&2; exit 1 ;; \
    esac; \
    TTYD_VER="1.7.7"; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl; \
    curl -fsSL \
      "https://github.com/tsl0922/ttyd/releases/download/${TTYD_VER}/ttyd.${TTYD_ARCH}" \
      -o /usr/local/bin/ttyd; \
    chmod +x /usr/local/bin/ttyd; \
    command -v ttyd; \
    ttyd --version; \
    rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    mkdir -p /etc/profile.d; \
    printf '%s\n' \
      '# Added by hermes-agent-ha-addon' \
      'export HERMES_STATE_ROOT=/config' \
      'export HERMES_HOME=/config/.hermes' \
      'export HOME=/config' \
      'export HERMES_INSTALL_DIR=/opt/hermes' \
      'case ":$PATH:" in' \
      '  *":/opt/hermes/.venv/bin:"*) ;;' \
      '  *) export PATH="/opt/hermes/.venv/bin:$PATH" ;;' \
      'esac' \
      >/etc/profile.d/hermes.sh; \
    chmod 644 /etc/profile.d/hermes.sh

RUN /opt/hermes/.venv/bin/pip install --no-cache-dir --disable-pip-version-check \
      'fastapi>=0.104.0,<1' 'uvicorn[standard]>=0.24.0,<1' || true

# Patch upstream HA platform so the WebSocket URL uses the Supervisor proxy
# endpoint (/core/websocket) instead of the hard-coded /core/api/websocket
# that v0.10.0 emits.  See patches/ha_ws_url.py for the full rationale —
# symptom is a tight reconnection loop with "502 Invalid response status"
# in the gateway logs.  Idempotent; safe on rebuild.
COPY patches/ /opt/hermes-ha-patches/
RUN /opt/hermes/.venv/bin/python3 /opt/hermes-ha-patches/ha_ws_url.py

# Pre-build the Hermes web UI at image build time so that `hermes dashboard`
# starts immediately on first boot without re-running npm install/build inside
# the container.  Without this, the build runs inside the container writable
# layer and is lost on every Rebuild — forcing a 30-60s delay plus a manual
# `npm install` workaround on the first request to /panel/.
# If the web/ directory or npm are absent in a future upstream image, the
# `|| true` makes this step non-fatal.
RUN set -eux; \
    if [ -d /opt/hermes/web ] && command -v npm >/dev/null 2>&1; then \
      cd /opt/hermes/web && npm install --prefer-offline && npm run build; \
    else \
      echo "[Dockerfile] web/ or npm not found — skipping pre-build (dashboard will build on first boot)"; \
    fi || true

COPY run.sh /run.sh
COPY hermes_ui/ /opt/hermes-ha-ui/

# Bake the version string from version.json into index.html at build time.
# Runtime substitution via server.py proved unreliable when HA doesn't pass
# --build-arg correctly.  Reading version.json here is the single source of
# truth and needs no ENV variable chain.
RUN python3 - <<'PYEOF'
import json, pathlib, sys
ui = pathlib.Path('/opt/hermes-ha-ui')
vf = ui / 'version.json'
if not vf.exists():
    print('[Dockerfile] version.json not found — skipping substitution', file=sys.stderr)
    sys.exit(0)
v = json.loads(vf.read_text())
html = (ui / 'index.html').read_text()
html = html.replace('{{ADDON_VERSION}}', 'v' + str(v.get('version', 'unknown')))
html = html.replace('{{HERMES_UPSTREAM}}', str(v.get('upstream', 'upstream')))
(ui / 'index.html').write_text(html)
print('[Dockerfile] version substituted:', v)
PYEOF

RUN chmod a+x /run.sh

ENTRYPOINT ["/run.sh"]
