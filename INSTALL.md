# Install Guide

## Add the repository to Home Assistant

1. In Home Assistant, open `Settings -> Add-ons -> Add-on Store`.
2. Open the overflow menu and choose `Repositories`.
3. Add your GitHub repository URL.
4. Open the new `Hermes Agent` add-on entry.

## Recommended first configuration

Use a narrow first-run setup:

- `llm_model`: defaults to `NousResearch/Hermes-4-14B`; for larger models use `NousResearch/Hermes-4-70B`, `NousResearch/Hermes-4-405B`, or `NousResearch/Hermes-4.3-36B`
- `auth_mode`: start with `api_key` unless you are intentionally validating the OpenAI Codex browser-login bridge
- `huggingface_api_key`: if using NousResearch models via HuggingFace Inference API (recommended for Hermes 4 series)
- `hf_base_url`: leave as `https://api-inference.huggingface.co/v1` unless using a custom HuggingFace endpoint
- `openrouter_api_key`: if using OpenRouter
- or `openai_base_url` + `openai_api_key`: if using any other OpenAI-compatible endpoint
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
5. The dedicated ttyd terminal page loads through **进入命令行面板** and keeps working on narrow mobile screens.
6. `GET /auth/status` returns a valid JSON auth bridge state.
7. In `auth_mode=api_key`, a test message returns a Hermes response inside the Web UI.
8. In `auth_mode=web_login`, the bridge can generate a login URL and store session state after callback exchange.

## Browser login status

`auth_mode=web_login` now covers login URL generation, callback exchange, refresh, logout, session persistence, and the local OpenAI-compatible shim route consumed by Hermes.
The main thing still left to validate in a live environment is your real OAuth client configuration.

## If startup fails

Check these first:

- Wrong or missing model credentials
- Unsupported model id in `llm_model`
- Pull failure for the upstream official Hermes image
- Too-broad Home Assistant watch settings creating noisy startup behavior
- Hermes API server not responding on the internal loopback port for the UI proxy
- Invalid auth bridge state under `/data/auth/session.json`

