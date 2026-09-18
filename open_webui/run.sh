#!/usr/bin/env bash
set -euo pipefail

echo "[open_webui] Initializing Open WebUI Add-on..."

CONFIG_PATH=/data/options.json
DATA_DIR=/config/open-webui

mkdir -p "${DATA_DIR}"
export DATA_DIR="${DATA_DIR}"
export PORT=8080
export WEBUI_BUILD_HASH="haos-addon"

# Parse HAOS add-on options
if [ -f "${CONFIG_PATH}" ]; then
  OPENAI_API_BASE_URL=$(jq -r '.openai_api_base_url // empty' "${CONFIG_PATH}")
  OPENAI_API_KEY=$(jq -r '.openai_api_key // empty' "${CONFIG_PATH}")
  OLLAMA_BASE_URL=$(jq -r '.ollama_base_url // empty' "${CONFIG_PATH}")
  WEBUI_AUTH=$(jq -r '.webui_auth // true' "${CONFIG_PATH}")
  WEBUI_NAME=$(jq -r '.webui_name // "Open WebUI"' "${CONFIG_PATH}")
  ENABLE_SIGNUP=$(jq -r '.enable_signup // true' "${CONFIG_PATH}")
  DEFAULT_MODELS=$(jq -r '.default_models // empty' "${CONFIG_PATH}")

  if [ -n "${OPENAI_API_BASE_URL}" ]; then
    export OPENAI_API_BASE_URL="${OPENAI_API_BASE_URL}"
    echo "[open_webui] Configured OPENAI_API_BASE_URL: ${OPENAI_API_BASE_URL}"
  fi

  if [ -n "${OPENAI_API_KEY}" ]; then
    export OPENAI_API_KEY="${OPENAI_API_KEY}"
    echo "[open_webui] Configured OPENAI_API_KEY (redacted)"
  fi

  if [ -n "${OLLAMA_BASE_URL}" ]; then
    export OLLAMA_BASE_URL="${OLLAMA_BASE_URL}"
    echo "[open_webui] Configured OLLAMA_BASE_URL: ${OLLAMA_BASE_URL}"
  fi

  export WEBUI_AUTH="${WEBUI_AUTH}"
  export WEBUI_NAME="${WEBUI_NAME}"
  export ENABLE_SIGNUP="${ENABLE_SIGNUP}"

  if [ -n "${DEFAULT_MODELS}" ]; then
    export DEFAULT_MODELS="${DEFAULT_MODELS}"
  fi
fi

# Ensure secret key exists for persistent web sessions
if [ ! -f "${DATA_DIR}/.webui_secret_key" ]; then
  head -c 32 /dev/urandom | base64 > "${DATA_DIR}/.webui_secret_key"
fi
export WEBUI_SECRET_KEY=$(cat "${DATA_DIR}/.webui_secret_key")

echo "[open_webui] Starting Open WebUI server on port ${PORT}..."
cd /app/backend
exec bash start.sh
