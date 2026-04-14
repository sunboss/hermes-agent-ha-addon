# Install Guide

## Add the repository to Home Assistant

1. In Home Assistant, open `Settings -> Add-ons -> Add-on Store`.
2. Open the overflow menu and choose `Repositories`.
3. Add your GitHub repository URL.
4. Open the new `Hermes Agent` add-on entry.

## Recommended first configuration

Use a narrow first-run setup:

- `llm_model`: defaults to `gpt-5.4` (pairs with the built-in OpenAI Codex
  ChatGPT-account web login).  **Must be an agentic / tool-calling model**:
  `gpt-5.4`, `gpt-4o`, `o3`, `o4-mini`, `claude-opus-4-6`,
  `claude-sonnet-4-6`, `gemini-2.5-pro`, `deepseek-v3`, `grok-4`, etc.
  **Do NOT use** `NousResearch/Hermes-*` (rejected by upstream), Llama
  base, or Mistral base.
- `auth_mode`: `web_login` (default) uses the ChatGPT-account bridge;
  attach your account by running `hermes auth login openai-codex` from
  the ttyd terminal once after first boot.  Switch to `api_key` if you
  prefer passing `openai_api_key` or `openrouter_api_key` directly.
- `openai_api_key` + `openai_base_url`: use for OpenAI, Azure OpenAI, or
  any OpenAI-compatible endpoint (incl. Anthropic via an OpenAI shim).
- `openrouter_api_key`: if using OpenRouter.
- `huggingface_api_key` / `hf_base_url`: optional, only useful once
  upstream Hermes Agent supports HuggingFace-hosted agentic models
  directly.  Not recommended for initial setup.
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

