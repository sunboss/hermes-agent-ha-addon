ARG BUILD_VERSION="2026.9.18.0"
ARG BUILD_FROM="lobehub/lobe-chat:latest"

FROM ${BUILD_FROM}

ARG BUILD_FROM
ARG BUILD_VERSION
ARG BUILD_ARCH

USER root

RUN apk add --no-cache jq bash ca-certificates || (apt-get update && apt-get install -y --no-install-recommends jq bash ca-certificates && rm -rf /var/lib/apt/lists/*)

COPY run.sh /run.sh
RUN chmod +x /run.sh

EXPOSE 3210
ENTRYPOINT ["/run.sh"]
