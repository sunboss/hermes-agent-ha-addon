ARG BUILD_VERSION="0.9.10"
# Pinned to the v2026.4.13 release (Hermes Agent v0.9.0) — pushed 2026-04-14.
# Update this digest when bumping to a newer Hermes release.
ARG HERMES_IMAGE_DIGEST="sha256:0ee58988876f5bb3d6e8e664542bbad2eb9453b9f8ef9a669afc87316087b357"

FROM nousresearch/hermes-agent@${HERMES_IMAGE_DIGEST}

ARG BUILD_VERSION

ENV HERMES_INSTALL_DIR=/opt/hermes
ENV HERMES_HOME=/data
ENV PATH=/opt/hermes/.venv/bin:$PATH
ENV HERMES_UI_PORT=8099
ENV HERMES_UI_DIR=/opt/hermes-ha-ui
ENV HERMES_TTYD_PORT=7681
# Upstream Hermes v2026.4.13 ships a local web dashboard launched via
# `hermes dashboard`.  It defaults to 127.0.0.1:9119.  We expose it to the
# browser via an HTTP reverse proxy at /panel/** in hermes_ui/server.py.
ENV HERMES_PANEL_HOST=127.0.0.1
ENV HERMES_PANEL_PORT=9119

LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="addon" \
  io.hass.arch="aarch64|amd64"

RUN set -eux; \
    printf "deb http://deb.debian.org/debian sid main\n" >/etc/apt/sources.list.d/ttyd-sid.list; \
    printf "Package: *\nPin: release a=unstable\nPin-Priority: 100\n\nPackage: ttyd\nPin: release a=unstable\nPin-Priority: 990\n" >/etc/apt/preferences.d/ttyd-sid; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates ttyd; \
    # Verify ttyd is installed and show its real path so run.sh can find it via PATH
    command -v ttyd; \
    ttyd --version; \
    rm -rf /var/lib/apt/lists/* /etc/apt/sources.list.d/ttyd-sid.list /etc/apt/preferences.d/ttyd-sid

# Guarantee the Hermes venv PATH is active in every shell spawned by ttyd.
# Background: the ttyd terminal previously invoked `/bin/bash -lc`, which runs
# /etc/profile on Debian.  /etc/profile resets PATH to the system default
# `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`, overriding
# the HERMES_INSTALL_DIR/.venv/bin prefix exported by run.sh.  That meant the
# `hermes` binary was silently unavailable inside the terminal — typing `hermes`
# gave "command not found", even though the gateway was happily running.
# Dropping a profile.d file makes bash (login OR non-login interactive) re-add
# the venv to PATH after /etc/profile has clobbered it.  HERMES_HOME and
# HERMES_INSTALL_DIR are re-exported for the same reason.
RUN set -eux; \
    mkdir -p /etc/profile.d; \
    printf '%s\n' \
      '# Added by hermes-agent-ha-addon v0.9.10 — ensures the Hermes venv is' \
      '# on PATH inside ttyd-spawned login shells even after /etc/profile runs.' \
      'export HERMES_HOME=/data' \
      'export HERMES_INSTALL_DIR=/opt/hermes' \
      'case ":$PATH:" in' \
      '  *":/opt/hermes/.venv/bin:"*) ;;' \
      '  *) export PATH="/opt/hermes/.venv/bin:$PATH" ;;' \
      'esac' \
      >/etc/profile.d/hermes.sh; \
    chmod 644 /etc/profile.d/hermes.sh

# Ensure the upstream dashboard dependencies (fastapi + uvicorn) are present
# in the Hermes venv.  The v2026.4.13 image should already ship them via the
# `web` extra, but we install them defensively here so `hermes dashboard` can
# never fail with ImportError at runtime.  `|| true` so an offline build of
# an already-satisfied venv doesn't fail the whole layer.
RUN /opt/hermes/.venv/bin/pip install --no-cache-dir --disable-pip-version-check \
      'fastapi>=0.104.0,<1' 'uvicorn[standard]>=0.24.0,<1' || true

COPY run.sh /run.sh
COPY hermes_ui/ /opt/hermes-ha-ui/
RUN chmod a+x /run.sh

ENTRYPOINT ["/run.sh"]