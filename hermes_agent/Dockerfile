ARG BUILD_VERSION="0.1.0"
ARG HERMES_REF="v0.8.0"

FROM ghcr.io/astral-sh/uv:0.11.6-python3.13-trixie@sha256:b3c543b6c4f23a5f2df22866bd7857e5d304b67a564f4feab6ac22044dde719b AS uv_source
FROM tianon/gosu:1.19-trixie@sha256:3b176695959c71e123eb390d427efc665eeb561b1540e82679c15e992006b8b9 AS gosu_source
FROM debian:13.4

ARG BUILD_VERSION
ARG HERMES_REF

ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/hermes/.playwright
ENV HERMES_INSTALL_DIR=/opt/hermes
ENV HERMES_HOME=/data/.hermes
ENV PATH=/opt/hermes/.venv/bin:$PATH

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      ca-certificates \
      ffmpeg \
      gcc \
      git \
      libffi-dev \
      nodejs \
      npm \
      procps \
      python3 \
      python3-dev \
      ripgrep && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -u 10000 -m -d /data hermes

COPY --chmod=0755 --from=gosu_source /gosu /usr/local/bin/gosu
COPY --chmod=0755 --from=uv_source /usr/local/bin/uv /usr/local/bin/uv
COPY --chmod=0755 --from=uv_source /usr/local/bin/uvx /usr/local/bin/uvx

RUN git clone https://github.com/NousResearch/hermes-agent.git "${HERMES_INSTALL_DIR}" && \
    cd "${HERMES_INSTALL_DIR}" && \
    git checkout "${HERMES_REF}" && \
    git submodule update --init --recursive

COPY custom_overlay/ /tmp/hermes-overlay/
RUN cp -a /tmp/hermes-overlay/. "${HERMES_INSTALL_DIR}/" && rm -rf /tmp/hermes-overlay

WORKDIR ${HERMES_INSTALL_DIR}

RUN npm install --prefer-offline --no-audit && \
    npx playwright install --with-deps chromium --only-shell && \
    cd "${HERMES_INSTALL_DIR}/scripts/whatsapp-bridge" && \
    npm install --prefer-offline --no-audit && \
    npm cache clean --force

RUN chown -R hermes:hermes "${HERMES_INSTALL_DIR}"
USER hermes
RUN uv venv && \
    uv pip install --no-cache-dir -e ".[all]"
USER root

LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="addon" \
  io.hass.arch="aarch64|amd64"

COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
