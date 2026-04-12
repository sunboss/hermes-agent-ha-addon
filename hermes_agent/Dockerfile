ARG BUILD_VERSION="0.6.0"
ARG HERMES_IMAGE_TAG="dafe443beba74384871e2c79d5b17db8bc51880e"

FROM nousresearch/hermes-agent:${HERMES_IMAGE_TAG}

ARG BUILD_VERSION

ENV HERMES_INSTALL_DIR=/opt/hermes
ENV HERMES_HOME=/data
ENV PATH=/opt/hermes/.venv/bin:$PATH
ENV HERMES_UI_PORT=8099
ENV HERMES_UI_DIR=/opt/hermes-ha-ui

LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="addon" \
  io.hass.arch="aarch64|amd64"

COPY run.sh /run.sh
COPY hermes_ui/ /opt/hermes-ha-ui/
RUN chmod a+x /run.sh

ENTRYPOINT ["/run.sh"]



