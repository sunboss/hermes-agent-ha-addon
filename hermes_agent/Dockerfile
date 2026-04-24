ARG BUILD_VERSION="2026.4.24.0"
# Upstream `latest` snapshot from 2026-04-23.  Newer than the last tagged
# release v2026.4.16 (2026-04-16).  Picked up because v2026.4.16 shipped
# with a `hermes dashboard` regression where the web UI first-boot
# `npm install` ran without sourcing the shell profile, so n/nvm-managed
# node was not on PATH and the build exited non-zero ("Web UI npm install
# failed").  Fixed upstream in commit series ending 2026-04-23 — see
# fix(terminal): auto-source ~/.profile and ~/.bash_profile.
# Revisit on the next tagged release (v2026.4.17+) and switch back to a
# release-tag digest.
ARG HERMES_IMAGE_DIGEST="sha256:7ab9fc410f95fb5e779f4fadbbd599e68ae37a9f25c4f657df8ff952e0172aee"

FROM nousresearch/hermes-agent@${HERMES_IMAGE_DIGEST}

ARG BUILD_VERSION
ARG BUILD_ARCH

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
    printf "deb http://deb.debian.org/debian sid main\n" >/etc/apt/sources.list.d/ttyd-sid.list; \
    printf "Package: *\nPin: release a=unstable\nPin-Priority: 100\n\nPackage: ttyd\nPin: release a=unstable\nPin-Priority: 990\n" >/etc/apt/preferences.d/ttyd-sid; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates ttyd; \
    command -v ttyd; \
    ttyd --version; \
    rm -rf /var/lib/apt/lists/* /etc/apt/sources.list.d/ttyd-sid.list /etc/apt/preferences.d/ttyd-sid

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
RUN chmod a+x /run.sh

ENTRYPOINT ["/run.sh"]
