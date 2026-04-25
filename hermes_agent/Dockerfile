ARG BUILD_VERSION="2026.4.25.2"
# BUILD_FROM is injected by HA Supervisor as --build-arg at build time
# (arch-specific, e.g. linux/arm64 on aarch64 hosts).  The default here
# is used when building outside of HA (e.g. local docker build).
#
# Pinned to a calendar tag (NOT :latest) so:
#   - upstream ship-day doesn't auto-pull an untested image
#   - rebuilds reuse the same Docker layer cache (1.78GB base layer)
#   - upgrades are an explicit, reviewable Dockerfile edit
# To upgrade: pick a newer tag from
# https://hub.docker.com/r/nousresearch/hermes-agent/tags and bump
# BUILD_VERSION below in lockstep.
ARG BUILD_FROM="nousresearch/hermes-agent:v2026.4.23"

FROM ${BUILD_FROM}

# ARGs declared above FROM go out of scope after FROM unless re-declared.
# Re-declaring inherits the value passed via --build-arg (or the default).
ARG BUILD_FROM
ARG BUILD_VERSION
ARG BUILD_ARCH

# Upstream :v2026.4.23+ ships with USER set to a non-root account, which
# breaks our chmod / install-into-/usr/local/bin steps.  Switch to root for
# the install layers; run.sh starts as root anyway (mkdir /etc/profile.d
# etc.) so the runtime user is unaffected.
USER root

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

# Build-time helper scripts.  Kept as standalone files (rather than
# Dockerfile RUN heredocs) so BuildKit's content-addressed cache keys on
# the script bytes — any edit here invalidates this layer and everything
# below, eliminating the "git updated but old script still runs" class of
# bugs we hit repeatedly with inline heredocs.  See scripts/install-ttyd.sh
# for the full rationale.
# --chmod sets executable bit during COPY itself, so no separate `chmod`
# step is needed (which previously failed with "Operation not permitted"
# when the upstream image's USER didn't own the destination).
COPY --chmod=0755 scripts/ /opt/hermes-ha-scripts/
RUN /opt/hermes-ha-scripts/install-ttyd.sh

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

# NOTE: an explicit `pip install fastapi uvicorn` step lived here through
# v2026.4.24.10.  The upstream v0.11.0 image (a) renamed/relocated its
# venv so the .venv/bin/pip path no longer existed, making the step a
# silent no-op (`|| true`), and (b) already bundles fastapi+uvicorn for
# `hermes dashboard`, so reinstalling them was redundant even when the
# path was correct.  Removed in v2026.4.25.1.

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

# Bake the version string from version.json into index.html.  Standalone
# script (see scripts/bake-version.py) for the cache-keying reasons
# documented above.
RUN python3 /opt/hermes-ha-scripts/bake-version.py

RUN chmod a+x /run.sh

ENTRYPOINT ["/run.sh"]
