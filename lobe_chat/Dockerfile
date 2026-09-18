ARG BUILD_VERSION="2026.9.18.1"
ARG BUILD_FROM="lobehub/lobe-chat:latest"

FROM ${BUILD_FROM}

ARG BUILD_FROM
ARG BUILD_VERSION
ARG BUILD_ARCH

# lobehub/lobe-chat is based on distroless / minimal node; do not install apk/apt
COPY entrypoint.js /app/ha_entrypoint.js

EXPOSE 3210
WORKDIR /app

ENTRYPOINT ["node", "/app/ha_entrypoint.js"]
