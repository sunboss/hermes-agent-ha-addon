ARG BUILD_VERSION="0.1.0"
ARG HERMES_IMAGE_TAG="dafe443beba74384871e2c79d5b17db8bc51880e"

FROM nousresearch/hermes-agent:${HERMES_IMAGE_TAG}

ARG BUILD_VERSION

ENV HERMES_INSTALL_DIR=/opt/hermes
ENV HERMES_HOME=/data/.hermes
ENV PATH=/opt/hermes/.venv/bin:$PATH

LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="addon" \
  io.hass.arch="aarch64|amd64"

COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
