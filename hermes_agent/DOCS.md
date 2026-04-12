# Hermes Agent

## What this add-on does

This add-on wraps the official Hermes Agent image and wires it into Home Assistant using the Supervisor proxy while staying close to the native Hermes Docker startup flow.

It updates:

- `/data/.env` for secrets and environment variables
- `/data/config.yaml` for Hermes runtime settings
- `/data/auth/session.json` for browser-login bridge state

It starts two processes:

- the official Hermes Docker entrypoint running `hermes gateway`
- a lightweight ingress-only web server on port `8099` that serves the built-in chat UI, exposes auth bridge state endpoints, and proxies the internal Hermes API server

The Hermes API server is enabled automatically on loopback so the ingress UI can talk to it without exposing an extra public port.

## Home Assistant access

The add-on uses the Supervisor proxy instead of requiring a manually created long-lived Home Assistant token.

- Home Assistant REST API: `http://supervisor/core/api/`
- Home Assistant WebSocket API: `ws://supervisor/core/websocket`
- Auth token: `SUPERVISOR_TOKEN`

## Recommended first setup

1. Set `llm_model`
2. Set `auth_mode=api_key` for the working chat path, or `auth_mode=web_login` if you want to validate the OpenAI Codex browser-login bridge
3. If using the working chat path, set either `openrouter_api_key` or `openai_base_url` + `openai_api_key`
4. Start with a narrow `watch_domains` list such as `climate`, `binary_sensor`, or `light`
5. Choose `terminal_backend` based on where Hermes should run shell commands
6. Leave `watch_all` disabled unless you really need every state change
7. Open the built-in Web UI from the add-on page after startup

## Browser login bridge

The add-on now includes a real session bridge for `auth_mode=web_login` + `auth_provider=openai_web`:

- persistent auth state under `/data/auth`
- `GET /auth/status` to inspect current bridge state
- `GET /auth/start` to generate a PKCE browser login URL
- `POST /auth/exchange` to submit the callback URL or authorization code
- `POST /auth/refresh` to refresh a stored session
- `POST /auth/logout` and `DELETE /auth/logout` to clear stored session state

Current limitation:

- this bridge manages the OpenAI Codex browser session, but it does not yet provide the OpenAI-compatible provider shim that Hermes would need to use that session for actual chat completions
- in practice, `auth_mode=web_login` is currently for login/session validation, while the actual chat path still uses `auth_mode=api_key`

## Upgrade workflow

1. Update `HERMES_IMAGE_TAG` in `Dockerfile`
2. Bump `version` in `config.yaml`
3. Rebuild and test the add-on
4. Publish only after verifying Hermes can start, the ingress UI loads, the auth bridge endpoints respond correctly, and the Hermes API proxy works successfully

## Known limitations

- The UI is focused on chat and control flow, not a full Lovelace-style control panel
- No automatic upstream image tracking by design
- The Web UI depends on the built-in Hermes OpenAI-compatible API server running inside the container
- `auth_mode=web_login` now stores, refreshes, and routes through a browser-session-backed provider shim, but it is still the newer path and should be treated as more experimental

