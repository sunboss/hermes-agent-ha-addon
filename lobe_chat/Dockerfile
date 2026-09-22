ARG BUILD_VERSION="2026.9.22.3"
ARG BUILD_FROM="lobehub/lobe-chat:latest"

FROM ${BUILD_FROM}

ARG BUILD_FROM
ARG BUILD_VERSION
ARG BUILD_ARCH

# Explicitly use root so the add-on can read /data/options.json written by HA Supervisor
USER root

COPY entrypoint.js /app/ha_entrypoint.js

EXPOSE 3210
WORKDIR /app

ENTRYPOINT ["node", "/app/ha_entrypoint.js"]
