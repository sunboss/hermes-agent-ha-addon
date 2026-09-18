#!/usr/bin/env bash
set -euo pipefail

echo "[lobe_chat] Initializing LobeChat Add-on..."

CONFIG_PATH=/data/options.json
export PORT=3210

if [ -f "${CONFIG_PATH}" ]; then
  OPENAI_PROXY_URL=$(jq -r '.openai_proxy_url // empty' "${CONFIG_PATH}")
  OPENAI_API_KEY=$(jq -r '.openai_api_key // empty' "${CONFIG_PATH}")
  ACCESS_CODE=$(jq -r '.access_code // empty' "${CONFIG_PATH}")
  DEFAULT_MODEL=$(jq -r '.default_model // empty' "${CONFIG_PATH}")

  if [ -n "${OPENAI_PROXY_URL}" ]; then
    export OPENAI_PROXY_URL="${OPENAI_PROXY_URL}"
    echo "[lobe_chat] Configured OPENAI_PROXY_URL: ${OPENAI_PROXY_URL}"
  fi

  if [ -n "${OPENAI_API_KEY}" ]; then
    export OPENAI_API_KEY="${OPENAI_API_KEY}"
    echo "[lobe_chat] Configured OPENAI_API_KEY (redacted)"
  fi

  if [ -n "${ACCESS_CODE}" ]; then
    export ACCESS_CODE="${ACCESS_CODE}"
    echo "[lobe_chat] Configured ACCESS_CODE protection"
  fi

  if [ -n "${DEFAULT_MODEL}" ]; then
    export DEFAULT_MODEL="${DEFAULT_MODEL}"
  fi
fi

# Ensure secret encryption key
export KEY_VAULTS_SECRET=$(head -c 32 /dev/urandom | base64)

echo "[lobe_chat] Starting LobeChat server on port ${PORT}..."
exec node /app/server.js
