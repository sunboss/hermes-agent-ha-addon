# Install Guide

## Add the repository to Home Assistant

1. In Home Assistant, open `Settings -> Add-ons -> Add-on Store`.
2. Open the overflow menu and choose `Repositories`.
3. Add your GitHub repository URL.
4. Open the new `Hermes Agent` add-on entry.

## Recommended first configuration

Use a narrow first-run setup:

- `llm_model`: your chosen model id
- `auth_mode`: start with `api_key` unless you are intentionally validating the OpenAI Codex browser-login bridge
- `openrouter_api_key`: if using OpenRouter
- or `openai_base_url` + `openai_api_key`: if using OpenAI-compatible endpoints
- `auth_provider`: leave `openai_web` for the browser-login path
- `auth_storage_path`: leave `/data/auth` unless you need a custom persistent location
- `openai_oauth_client_id`: required only for `auth_mode=web_login`
- `openai_oauth_redirect_uri`: keep the default loopback callback unless your OAuth client is registered differently
- `openai_oauth_scopes`: keep the default unless your provider setup requires a different scope set
- `terminal_backend`: start with `local` unless you specifically need another Hermes backend
- `watch_domains`: start with `climate`, `binary_sensor`, or `light`
- `watch_all`: keep `false`
- `cooldown_seconds`: leave `30`
- `api_server_key`: optional, only if you want to override the auto-generated key used by the built-in Web UI proxy

## First boot validation

After starting the add-on, check the logs for these milestones:

1. The wrapper script starts without shell errors.
2. Hermes writes `/data/.env`, `/data/config.yaml`, and `/data/auth/session.json`.
3. Hermes starts the gateway successfully.
4. The ingress UI becomes available through `OPEN WEB UI`.
5. `GET /auth/status` returns a valid JSON auth bridge state.
6. In `auth_mode=api_key`, a test message returns a Hermes response inside the Web UI.
7. In `auth_mode=web_login`, the bridge can generate a login URL and store session state after callback exchange.

## Important current limitation

`auth_mode=web_login` now covers login URL generation, callback exchange, refresh, logout, and session persistence.
It does not yet include the OpenAI-compatible provider shim that would let Hermes use that stored browser session for chat completions.
For actual chatting today, keep using `auth_mode=api_key`.

## If startup fails

Check these first:

- Wrong or missing model credentials
- Unsupported model id in `llm_model`
- Pull failure for the upstream official Hermes image
- Too-broad Home Assistant watch settings creating noisy startup behavior
- Hermes API server not responding on the internal loopback port for the UI proxy
- Invalid auth bridge state under `/data/auth/session.json`

