ARG BUILD_VERSION="0.7.1"
ARG HERMES_IMAGE_TAG="dafe443beba74384871e2c79d5b17db8bc51880e"
ARG TTYD_VERSION="1.7.7"

FROM nousresearch/hermes-agent:${HERMES_IMAGE_TAG}

ARG BUILD_VERSION
ARG TTYD_VERSION
ARG TARGETARCH

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
    case "${TARGETARCH}" in \
      amd64) ttyd_arch="x86_64" ;; \
      arm64) ttyd_arch="aarch64" ;; \
      *) echo "Unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    apt-get update; \
    apt-get install -y --no-install-recommends curl ca-certificates; \
    curl -fsSL "https://github.com/tsl0922/ttyd/releases/download/${TTYD_VERSION}/ttyd.${ttyd_arch}" -o /usr/local/bin/ttyd; \
    chmod +x /usr/local/bin/ttyd; \
    ttyd --version; \
    rm -rf /var/lib/apt/lists/*

COPY run.sh /run.sh
COPY hermes_ui/ /opt/hermes-ha-ui/
RUN chmod a+x /run.sh

ENTRYPOINT ["/run.sh"]