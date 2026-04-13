# Changelog

## 0.9.1

### Root-cause fixes (from official Hermes docs)

- **Critical — Connection Refused**: `entrypoint.sh gateway` changed to
  `entrypoint.sh gateway run`. Per the official docs, `hermes gateway` without
  the `run` subcommand attempts to register a systemd/launchd background service,
  which does not exist inside a Docker container. The gateway exited immediately,
  leaving port 8642 unbound and causing every chat request to return
  `Connection Refused`. Using `gateway run` forces true foreground execution
  (the officially recommended mode for Docker/WSL).

- **`/v1/models` returns wrong name**: Added `API_SERVER_MODEL_NAME` env var in
  `run.sh` so the Hermes gateway advertises the configured `llm_model` value
  instead of the default profile name. The UI model picker now shows the real
  model ID (e.g. `NousResearch/Hermes-4-14B`).

### JS execution fixes

- **Page showed English default text** (JS not running): All dynamic text is now
  pre-filled as static Chinese content directly in `index.html`. The page is fully
  readable and usable even if JavaScript is completely blocked (e.g. by a strict
  Content Security Policy from Home Assistant Ingress).

- Added `id="js-error-banner"` red banner that appears when `app.js` fails to
  load (file not found, CSP block, network error). The `<script onerror>` handler
  reveals it automatically.

- Added `window.onerror` and `window.onunhandledrejection` handlers at the top of
  `app.js` to catch runtime JS errors and display them in the banner.

- Replaced all bare `document.getElementById(...).textContent = ...` calls in
  `applyStaticText()` with a null-safe `setText(id, text)` helper. A missing
  element now logs a console warning instead of throwing `TypeError` and stopping
  the rest of the function.

- `authTitle`, `authInput`, auth buttons, and other module-level DOM bindings now
  guarded with `if (el)` before assignment to prevent null-ref crashes.

## 0.9.0

### Bug fixes
- **Critical** — Fixed health check in UI always showing "不可用": `checkHealth()` was
  fetching `./api/health` (proxied to the Hermes gateway, which is not ready at startup).
  Changed to `./health` which hits the local UI server immediately.
- **Critical** — Fixed model list always showing "不可用": `loadModels()` was fetching
  `./api/v1/models` which the Hermes gateway does not expose. Added a local `/models`
  endpoint in `server.py` backed by the provider shim's `list_models()`, and updated
  `app.js` to call `./models` instead.
- **Important** — Fixed `TTYD_ROOT_PATHS = {"/token", "/ws"}` silently proxying any
  request to `/ws` or `/token` through to ttyd. ttyd is started with `--base-path /ttyd`
  so its paths are `/ttyd/ws` and `/ttyd/token`. Cleared `TTYD_ROOT_PATHS` to an empty set.
- **Important** — Fixed ttyd terminal launching with `--noprofile --norc` which prevented
  the Hermes virtualenv PATH from loading. Changed to `bash -lc` so `.profile` is sourced.
- **Important** — Added `ingress_stream: true` to `config.yaml` to prevent Home Assistant
  Ingress from buffering long agent responses.
- **Minor** — Fixed `_proxy_api` sending `Authorization: Bearer ` (with empty key) when
  `API_SERVER_KEY` is blank; the header is now omitted entirely in that case.
- Fixed `extractAssistantText()` only handling the OpenAI `choices` format; now also
  handles Hermes `output_text`, `output[]` array, and plain `message`/`content` shapes.

### New features & optimizations
- `/health` endpoint now also pings the Hermes gateway (`API_BASE/health`) and returns
  `"gateway": "ready"|"starting"`. The UI displays a distinct amber "网关启动中" state
  and auto-retries every 5 s until the gateway is fully up.
- Added a "Hermes 正在思考…" placeholder bubble in the chat log while waiting for a
  response, so users have clear visual feedback that the request is in flight.
- Bumped `HERMES_DEFAULT_MAX_TOKENS` from 4096 → 8192 (Hermes 4 supports 32k+ context).
- `server_version` updated from `HermesIngressUI/0.6` → `HermesIngressUI/0.9`.
- Added `#health-status[data-state="warning"]` CSS rule (amber colour) for the new
  gateway-starting state.

### Documentation
- Added full module docstrings to `server.py`, `auth_bridge.py`, and `provider_shim.py`
  describing architecture, routing, security model, environment variables, and public API.
  This makes it straightforward for other developers (or AI assistants) to understand and
  extend each module without reading the full source.
- Added a file-level JSDoc header to `app.js` explaining URL routing, client state, and
  how to add new UI features.
- Added detailed section banners to `run.sh` documenting the six startup stages and all
  `options.json` keys.

## 0.8.0

- Add first-class support for NousResearch Hermes 4 series models from HuggingFace.
- New config options: `huggingface_api_key` and `hf_base_url` for the HuggingFace Inference API.
- Default `llm_model` changed from empty string to `NousResearch/Hermes-4-14B`.
- `provider_shim.py` rewritten to support three provider backends: HuggingFace Inference API (primary for Hermes 4), generic OpenAI-compatible endpoints, and OpenAI Codex web-login. Provider is selected automatically based on which credentials are set.
- NousResearch Hermes 4 ChatML sampling defaults applied automatically: temperature=0.6, top_p=0.95, top_k=20, max_tokens=4096.
- `list_models` endpoint now advertises all four Hermes 4 series models in the UI model picker.
- Fixed bogus `OPENAI_SHIM_MODEL` fallback `gpt-5.4` — now defaults to `NousResearch/Hermes-4-14B`.
- Fixed `yaml.safe_dump(allow_unicode=False)` in `run.sh` which would corrupt non-ASCII entity names and config values by replacing them with escape sequences; changed to `allow_unicode=True`.
- Fixed literal `\`r\`n` escape sequences in `README.md` and `INSTALL.md` (malformed CRLF artifacts appearing as raw text).
- Fixed duplicate step number in `INSTALL.md` first-boot validation checklist (two items numbered 5).
- Fixed double-redirect bug in `terminal.html`: both `<meta http-equiv="refresh">` and `window.location.replace()` were present; removed the `meta` tag and kept only the JS redirect.
- Updated `translations/en.yaml` to document the new `huggingface_api_key` and `hf_base_url` options and updated the `llm_model` description to list Hermes 4 series variants.
- Updated `DOCS.md` with Hermes 4 model table, ChatML parameter reference, and HuggingFace setup instructions.
- Updated `README.md` and `INSTALL.md` with Hermes 4 model options and HuggingFace API key instructions.

## 0.1.0

- Initial Home Assistant add-on scaffold for Hermes Agent.
- Wraps the official Hermes image with pinned upstream tag `dafe443beba74384871e2c79d5b17db8bc51880e`.
- Injects Supervisor API access into Hermes Home Assistant integration.
- Generates Hermes config and env files from add-on options at startup.
