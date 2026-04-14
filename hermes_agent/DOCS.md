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

1. Set `llm_model` to an agentic model ID.  The default `gpt-5.4` pairs
   with the built-in OpenAI Codex ChatGPT-account web login (no API key
   needed after a one-time `hermes auth login openai-codex` in the ttyd
   terminal).  Override with anything agentic: `claude-opus-4-6`,
   `claude-sonnet-4-6`, `gemini-2.5-pro`, `deepseek-v3`, `gpt-4o`, `o3`,
   `o4-mini`, `grok-4`, …
2. Leave `auth_mode=web_login` if you want the ChatGPT-account path.
   Switch to `auth_mode=api_key` if you'd rather pass a raw key:
   - `openai_api_key` + `openai_base_url` for OpenAI / Anthropic (via
     OpenAI-compatible shim) / Azure OpenAI / any OpenAI-compatible
     endpoint
   - `openrouter_api_key` for OpenRouter
3. Start with a narrow `watch_domains` list such as `climate`,
   `binary_sensor`, or `light`.
4. Choose `terminal_backend` based on where Hermes should run shell
   commands.
5. Leave `watch_all` disabled unless you really need every state change.
6. Open the built-in Web UI from the add-on page after startup.

## Which models actually work?

Hermes Agent is an **agent framework** that requires tool-calling-capable
models.  It is NOT a wrapper around Nous Research Hermes (the LLM series).
The upstream gateway will reject non-agentic models at runtime with:

```
⚠  Nous Research Hermes 3 & 4 models are NOT agentic and are not designed
   for use with Hermes Agent. They lack tool-calling capabilities required
   for agent workflows.
```

**Supported agentic models** (pick whichever your provider exposes):

| Family   | Example IDs                                        |
|----------|----------------------------------------------------|
| OpenAI   | `gpt-5.4`, `gpt-4o`, `o3`, `o4-mini`               |
| Anthropic| `claude-opus-4-6`, `claude-sonnet-4-6`             |
| Google   | `gemini-2.5-pro`, `gemini-2.0-flash`               |
| DeepSeek | `deepseek-v3`, `deepseek-r1`                       |
| xAI      | `grok-4`                                           |

**NOT supported** (will 400 on every chat turn): `NousResearch/Hermes-*`,
Llama base, Mistral base, Qwen base, any non-tool-calling model.

> Historical note: versions 0.8.0–0.9.10 of this add-on shipped with
> `llm_model: "NousResearch/Hermes-4-14B"` as the default.  That was
> wrong — it predated the v2026.4.13 upstream warning.  v0.9.11 migrates
> any existing config with a `NousResearch/Hermes-*` model.default back
> to `gpt-5.4` automatically on next boot.

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

Since v0.9.9 the upgrade procedure is documented in full in
[`../docs/UPGRADE_LOG.md`](../docs/UPGRADE_LOG.md). The short version:

1. Update `HERMES_IMAGE_DIGEST` (sha256) and `BUILD_VERSION` in `Dockerfile`
2. Bump `version` in `config.yaml`
3. Run through the pitfalls checklist in
   [`../docs/ARCHITECTURE.md` §7](../docs/ARCHITECTURE.md#7-common-pitfalls-checklist-for-future-upgrades)
4. Add a changelog entry **and** a root-cause entry in `UPGRADE_LOG.md`
5. Rebuild, recreate the container (not just restart — state bugs only
   surface when the writable layer is wiped), and test
6. Publish only after verifying Hermes can start, `HERMES_HOME=/data` inside
   the gateway process, the ingress UI loads, `/config-model` returns the
   right model, ttyd works, and the Hermes API proxy handles chat requests

**Critical landmine:** do not call `/opt/hermes/docker/entrypoint.sh` from
`run.sh`. It hardcodes `HERMES_HOME=/opt/data` and will silently break auth
persistence. See `docs/UPGRADE_LOG.md` → "v0.9.9 — `HERMES_HOME` hardcoded"
for the full root-cause writeup.

## Known limitations

- The UI is focused on chat and control flow, not a full Lovelace-style control panel
- No automatic upstream image tracking by design
- The Web UI depends on the built-in Hermes OpenAI-compatible API server running inside the container
- `auth_mode=web_login` now stores, refreshes, and routes through a browser-session-backed provider shim, but it is still the newer path and should be treated as more experimental

