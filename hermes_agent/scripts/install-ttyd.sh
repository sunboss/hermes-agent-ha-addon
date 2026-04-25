#!/bin/sh
# Install ttyd into /usr/local/bin/ttyd.
#
# Why a standalone script (instead of a RUN heredoc in the Dockerfile):
#   - HA Supervisor's BuildKit handles `RUN ... \` line-continued commands
#     containing nested heredocs unreliably, and its layer cache keying is
#     based on the literal RUN string — small in-Dockerfile edits to the
#     heredoc body have repeatedly failed to invalidate the cache, leaving
#     the container running an old script. COPY-then-RUN of a script file
#     keys the cache on the script's content hash, so any edit here is
#     guaranteed to trigger a rebuild of this layer and everything below.
#   - We deliberately avoid `apt-get` because the upstream
#     nousresearch/hermes-agent:latest arm64 image ships with broken apt
#     sources (exit 100), and the sid `ttyd` package is unavailable on
#     arm64 anyway (exit 2). See docs/UPGRADE_LOG.md.
#   - We deliberately avoid `curl`/`wget` because ca-certificates is not
#     guaranteed to be present and we cannot install it via apt. Python's
#     stdlib urllib + an unverified SSL context sidesteps both problems.

set -eu

if command -v ttyd >/dev/null 2>&1; then
    echo "[install-ttyd] ttyd already in base image: $(ttyd --version 2>&1 | head -1)"
    exit 0
fi

case "$(uname -m)" in
    aarch64|arm64) TTYD_ARCH="aarch64" ;;
    x86_64|amd64)  TTYD_ARCH="x86_64"  ;;
    *) echo "[install-ttyd] Unsupported arch: $(uname -m)" >&2; exit 1 ;;
esac

TTYD_VERSION="1.7.7"
TTYD_URL="https://github.com/tsl0922/ttyd/releases/download/${TTYD_VERSION}/ttyd.${TTYD_ARCH}"

echo "[install-ttyd] downloading ${TTYD_URL}"

python3 /opt/hermes-ha-scripts/_fetch.py "${TTYD_URL}" /usr/local/bin/ttyd
chmod 0755 /usr/local/bin/ttyd

echo "[install-ttyd] installed: $(ttyd --version 2>&1 | head -1)"
