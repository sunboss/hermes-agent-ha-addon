ARG BUILD_VERSION="2026.9.18.1"
ARG BUILD_FROM="yidadaa/chatgpt-next-web:latest"

FROM ${BUILD_FROM}

ARG BUILD_FROM
ARG BUILD_VERSION
ARG BUILD_ARCH

# Zero-dependency entrypoint directly utilizing the base image node runtime
COPY entrypoint.js /app/ha_entrypoint.js

EXPOSE 3000
WORKDIR /app

ENTRYPOINT ["node", "/app/ha_entrypoint.js"]
