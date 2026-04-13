ARG BUILD_VERSION="0.9.2"
ARG HERMES_IMAGE_TAG="dafe443beba74384871e2c79d5b17db8bc51880e"

FROM nousresearch/hermes-agent:${HERMES_IMAGE_TAG}

ARG BUILD_VERSION

ENV HERMES_INSTALL_DIR=/opt/hermes
ENV HERMES_HOME=/data
ENV PATH=/opt/hermes/.venv/bin:$PATH
ENV HERMES_UI_PORT=8099
ENV HERMES_UI_DIR=/opt/hermes-ha-ui
ENV HERMES_TTYD_PORT=7681

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

COPY run.sh /run.sh
COPY hermes_ui/ /opt/hermes-ha-ui/
RUN chmod a+x /run.sh

ENTRYPOINT ["/run.sh"]