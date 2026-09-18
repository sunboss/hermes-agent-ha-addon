#!/usr/bin/env bash
set -euo pipefail

echo "[next_chat] Initializing NextChat Add-on..."

CONFIG_PATH=/data/options.json
export PORT=3000

if [ -f "${CONFIG_PATH}" ]; then
  BASE_URL=$(jq -r '.base_url // empty' "${CONFIG_PATH}")
  API_KEY=$(jq -r '.api_key // empty' "${CONFIG_PATH}")
  ACCESS_CODE=$(jq -r '.access_code // empty' "${CONFIG_PATH}")
  CUSTOM_MODELS=$(jq -r '.custom_models // empty' "${CONFIG_PATH}")

  if [ -n "${BASE_URL}" ]; then
    export BASE_URL="${BASE_URL}"
    echo "[next_chat] Configured BASE_URL: ${BASE_URL}"
  fi

  if [ -n "${API_KEY}" ]; then
    export OPENAI_API_KEY="${API_KEY}"
    echo "[next_chat] Configured OPENAI_API_KEY (redacted)"
  fi

  if [ -n "${ACCESS_CODE}" ]; then
    export CODE="${ACCESS_CODE}"
    echo "[next_chat] Configured access CODE"
  fi

  if [ -n "${CUSTOM_MODELS}" ]; then
    export CUSTOM_MODELS="${CUSTOM_MODELS}"
  fi
fi

echo "[next_chat] Starting NextChat server on port ${PORT}..."
exec node server.js
