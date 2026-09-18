ARG BUILD_VERSION="2026.9.18.0"
ARG BUILD_FROM="ghcr.io/open-webui/open-webui:main"

FROM ${BUILD_FROM}

ARG BUILD_FROM
ARG BUILD_VERSION
ARG BUILD_ARCH

USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends jq curl ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY run.sh /run.sh
RUN chmod +x /run.sh

WORKDIR /app/backend

ENTRYPOINT ["/run.sh"]
