# Hermes Agent

## What this add-on does

This add-on wraps the official Hermes Agent image and wires it into Home Assistant using the Supervisor proxy while staying close to the native Hermes Docker startup flow.

It updates:

- `/data/.env` for secrets and environment variables
- `/data/config.yaml` for Hermes runtime settings

It starts two processes:

- the official Hermes Docker entrypoint running `hermes gateway`
- a lightweight ingress-only web server on port `8099` that serves the built-in chat UI and proxies the internal Hermes API server

The Hermes API server is enabled automatically on loopback so the ingress UI can talk to it without exposing an extra public port.

## Home Assistant access

The add-on uses the Supervisor proxy instead of requiring a manually created long-lived Home Assistant token.

- Home Assistant REST API: `http://supervisor/core/api/`
- Home Assistant WebSocket API: `ws://supervisor/core/websocket`
- Auth token: `SUPERVISOR_TOKEN`

## Recommended first setup

1. Set `llm_model`
2. Set either `openrouter_api_key` or `openai_base_url` + `openai_api_key`
3. Start with a narrow `watch_domains` list such as `climate`, `binary_sensor`, or `light`
4. Choose `terminal_backend` based on where Hermes should run shell commands
5. Leave `watch_all` disabled unless you really need every state change
6. Open the built-in Web UI from the add-on page after startup

## Upgrade workflow

1. Update `HERMES_IMAGE_TAG` in `Dockerfile`
2. Bump `version` in `config.yaml`
3. Rebuild and test the add-on
4. Publish only after verifying Hermes can start, the ingress UI loads, and the Hermes API proxy works successfully

## Known limitations in this scaffold

- The first UI version is focused on chat, not a full Lovelace-style control panel
- No automatic upstream image tracking by design
- The Web UI depends on the built-in Hermes OpenAI-compatible API server running inside the container
