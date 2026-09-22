ARG BUILD_VERSION="2026.9.22.4"
ARG BUILD_FROM="yidadaa/chatgpt-next-web:latest"

FROM ${BUILD_FROM}

ARG BUILD_FROM
ARG BUILD_VERSION
ARG BUILD_ARCH

USER root

COPY entrypoint.js /app/ha_entrypoint.js

EXPOSE 3000
WORKDIR /app

ENTRYPOINT ["node", "/app/ha_entrypoint.js"]
