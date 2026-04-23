# Upgrade Log & Fix Register

> Companion to [`ARCHITECTURE.md`](./ARCHITECTURE.md). This file records the
> **root cause** behind each shipped fix, not just the one-liner in the
> changelog. Read this before attempting any upgrade so you don't re-break
> things that have already been fixed once.
>
> Future AI agents: when asked to upgrade or debug this repo, **grep this
> file for the symptom the user describes before assuming it's a new bug**.

---

## Upgrade workflow (authoritative)

1. Read [`ARCHITECTURE.md` §7](./ARCHITECTURE.md#7-common-pitfalls-checklist-for-future-upgrades)
   end to end.
2. Find the new upstream digest:
   ```bash
   docker pull nousresearch/hermes-agent:<tag>
   docker inspect nousresearch/hermes-agent:<tag> \
     --format '{{index .RepoDigests 0}}'
   ```
3. Update `hermes_agent/Dockerfile`:
   - `ARG BUILD_VERSION="<new add-on version>"`
   - `ARG HERMES_IMAGE_DIGEST="sha256:…"`
4. Read the upstream release notes, specifically watching for:
   - Changes to `/opt/hermes/docker/entrypoint.sh` — if it still hardcodes
     `HERMES_HOME=/opt/data`, keep the bypass in `run.sh` (§ v0.9.9 below).
   - Changes to `config.yaml` schema (e.g. `model` string → dict in v2026.4.13).
   - Removed env vars (e.g. `LLM_MODEL` in v2026.4.13).
   - New first-boot bootstrap steps that upstream `entrypoint.sh` runs but
     our `run.sh` bypasses. Replicate them manually in `run.sh` step 6.
5. Bump `hermes_agent/config.yaml` `version:` to match `BUILD_VERSION`.
6. Add an entry to `hermes_agent/CHANGELOG.md`.
7. Add an entry to this file under "Fix register" with the root cause.
8. Run the pitfalls checklist against a local build (or a staging HA instance).
9. Commit, push, open PR.

---

## Fix register

Each entry documents **what broke, why, and how we fixed it** so that future
upgrades don't regress the same landmine.

### v0.10.4 — `MESSAGING_CWD` deprecation warning still firing (v0.10.2 regression)

Shipped: 2026-04-23. Same upstream as v0.10.2/v0.10.3.

**Symptom**
Even after v0.10.2's `env_map.pop("MESSAGING_CWD", None)` fix, every boot still logs:

```
⚠ Deprecated .env settings detected:
  ⚠ MESSAGING_CWD=/config/addons_data/hermes-agent/workspace found in .env
    — this is deprecated.
```

The `.env` file on disk is genuinely clean (no `MESSAGING_CWD=` line). The
warning persists anyway.

**Root cause**
The v0.10.2 fix was incomplete. To keep ttyd's `cd` fallback working without
putting the value in `.env`, it wrote `export MESSAGING_CWD=...` into
`${HERMES_HOME}/.addon-runtime` and had `run.sh` source that file after `.env`.

But Hermes v0.10.0's deprecation check reads `os.environ`, not just the
`.env` file. Because run.sh sourced `.addon-runtime`, MESSAGING_CWD ended up
in the process environment. The gateway's upstream check then reported it
with the misleading text "found in .env" — its error message hardcodes the
filename, even when the value actually came from environ. We were chasing
the wrong layer.

**Fix**
- Renamed the side-file variable from `MESSAGING_CWD` to `TTYD_CWD`. The
  name collision with the deprecated Hermes env var is what triggered the
  warning; picking a distinct name makes it impossible for the upstream
  check to match.
- Dropped `export` from the side file. It now emits a plain `TTYD_CWD="..."`
  line that `run.sh` parses with `sed` into a *local* bash variable — never
  an exported one. The Hermes gateway inherits nothing from this path.
- Changed the ttyd command from env-var fallback to positional argument:
  `bash -c 'cd "$1" && exec bash -i' _ "${TTYD_CWD}"`. This bypasses
  environment entirely for the cwd hand-off.
- Added `unset MESSAGING_CWD` right after `.env` is sourced, as
  belt-and-suspenders against any stale `MESSAGING_CWD=...` still sitting
  in an old `.env` (e.g. if a user downgraded then upgraded).

**Invariants**
- Never name a side-channel variable with a prefix that matches an upstream
  deprecated env var (`MESSAGING_*`, `HERMES_*`, `LLM_*`, etc.). Upstream
  scans `os.environ` for these patterns.
- If you *must* communicate a value from `run.sh` to a child process that
  is NOT the Hermes gateway (e.g. ttyd), prefer positional arguments or a
  pipe, not exported env vars.
- On every upstream bump, grep the upstream source for
  `DEPRECATED` / `deprecat` inside `gateway/` to see which env var names
  are landmines.

### v0.10.3 — `server.py` mojibake SyntaxError

Shipped: 2026-04-23. Same upstream as v0.10.2.

**Symptom**
On container start the add-on logs:

```
  File "/opt/hermes-ha-ui/server.py", line 263
    "message": f"浠ｇ悊璇锋眰澶辫触锛歿type(exc).__name__}",
                                              ^
SyntaxError: f-string: single '}' is not allowed
```

The ingress UI server (`hermes_ui/server.py`) fails to start. Every user-
visible surface — the launcher page at `/`, the `/panel/` proxy, `/ttyd/`,
`/health` — returns 502 Bad Gateway through HA Ingress. The underlying
gateway is still running, but the user cannot reach any of it.

**Root cause**
The file was UTF-8 encoded, containing Chinese status messages like
`代理请求失败：{type(exc).__name__}`. At some point (likely an editor-on-
Windows save during the v0.10.0 storage-layout refactor) the file was
re-opened with the wrong encoding — its UTF-8 bytes were misread as GBK
characters — and then saved again as UTF-8. The result is
"mojibake-squared": the file is valid UTF-8, but the text is garbage
Chinese like `浠ｇ悊璇锋眰澶辫触锛歿`.

On most of the corrupted strings this only manifests as ugly error
messages. But on line 263 specifically, the full-width colon `：`
(U+FF1A, 3 UTF-8 bytes `EF BC 9A`) was followed immediately by `{`.
When those 4 bytes were decoded as GBK, the opening `{` got absorbed
into a multi-byte character, producing `歿` with no `{` left to start
the f-string interpolation. That turned a valid f-string into a syntax
error.

A UTF-8 BOM (`EF BB BF`) was also added at file start during the same
save — not a Python error on its own (Python tolerates a BOM), but
noise worth cleaning up.

**Fix**
- Reversed the mojibake by treating the current UTF-8 chars as GBK
  bytes and decoding them back as UTF-8: recovers ~95% of the original
  Chinese. Lost characters (`—`, `→`, `…`, `│` — none of which exist in
  GBK) were recovered by cross-referencing the pre-corruption
  `hermes_ui/server.py` at commit `223f295` (v0.9.11), which was the
  last clean version.
- Hand-reconstructed 4 lines that were added *after* v0.9.11 (in the
  new `/panel/` proxy block) and so had no clean reference — the Chinese
  there was rewritten from code context.
- Stripped the BOM so future `ast.parse()` and `git diff` don't include
  the invisible `\ufeff` marker.
- Updated the in-file `Version:` docstring from the stale `0.9.11` to
  the current `0.10.3`.

**Invariants**
- `hermes_ui/server.py` must stay **UTF-8 without BOM**. Any editor
  that auto-inserts a BOM or re-saves as GBK will immediately re-break
  this. When editing on Windows, set VS Code's `files.encoding: utf8`
  and `files.autoGuessEncoding: false`.
- Pre-commit check recommendation: run
  `python3 -c "import ast; ast.parse(open('hermes_agent/hermes_ui/server.py', encoding='utf-8').read())"`
  before every commit — catches both encoding corruption and plain
  syntax errors.
- When replacing text in this file, always go through the `Edit` tool
  (exact-match semantics), never a `sed` pipeline that might reinterpret
  the encoding.

### v0.10.2 — HA WebSocket 502 loop + `MESSAGING_CWD` deprecation

Shipped: 2026-04-23. Upstream still `v2026.4.16 / v0.10.0`
(`sha256:14ba9a26cf2d498ea773f1825326c404795ec4cb436a9479d22b7a345396c370`).

#### Fix 1 — HA WebSocket reconnection loop (`502 Invalid response status`)

**Symptom**
Immediately after the gateway prints `✓ Web UI built`, the Home Assistant
platform adapter spams reconnect failures:

```
WARNING gateway.platforms.homeassistant: [Homeassistant] Reconnection failed:
  502, message='Invalid response status',
  url='ws://supervisor/core/api/websocket'
```

Every 2–3 seconds, forever. HA state changes never reach the gateway, so
Hermes has zero situational awareness of the house.

**Root cause**
Upstream `hermes.gateway.platforms.homeassistant._ws_connect()` hard-codes
the WebSocket URL suffix:

```python
ws_url = self._hass_url.replace("http://", "ws://").replace("https://", "wss://")
ws_url = f"{ws_url}/api/websocket"
```

For direct HA Core (`http://homeassistant.local:8123/api/websocket`) that
suffix is correct. But **every** HA add-on reaches HA through the
Supervisor proxy, whose endpoint map is:

| Protocol | Path                      | Proxies to                        |
|----------|---------------------------|-----------------------------------|
| HTTP     | `/core/api/*`             | HA Core REST API (`/api/*`)        |
| WS       | `/core/websocket`         | HA Core WebSocket (`/api/websocket`) |

Notice the asymmetry: REST keeps `/api`, WS drops it. With
`HASS_URL=http://supervisor/core`, the upstream code builds
`ws://supervisor/core/api/websocket` — an endpoint the Supervisor proxy
doesn't expose, hence the 502.

Upstream v0.10.0 offers **no env var or config key** to override the WS
URL path (verified by reading the source). So we have to patch the
installed Python module in place.

**Fix**
New `hermes_agent/patches/ha_ws_url.py`, invoked from the Dockerfile after
the venv is finalized. Regex-matches the hard-coded assignment line,
captures its leading indent, and replaces it with a conditional:

```python
if 'supervisor' in (self._hass_url or ''):
    ws_url = f"{ws_url}/websocket"        # Supervisor proxy mode
else:
    ws_url = f"{ws_url}/api/websocket"    # direct HA Core (original)
```

Idempotent — a marker comment prevents re-patching. Non-fatal — if the
upstream refactors the pattern away, the script logs a warning and exits 0
so the image still builds; the next release just needs a new patch target.

**Invariants**
- Never change `HASS_URL` away from `http://supervisor/core`. The REST path
  (`/api/services/...`) is correct as-is; only the WS suffix was wrong.
- If upstream ever adds a native `ws_url` override (env var or
  `platforms.homeassistant.ws_url`), delete this patch and use the
  supported interface.
- On every upstream upgrade, verify the patch still applies:
  `docker run ... python3 /opt/hermes-ha-patches/ha_ws_url.py` should
  print `applied` on first build and `already applied` on rebuild.

#### Fix 2 — `MESSAGING_CWD` removed from `.env`

**Symptom**
On every boot, upstream prints:

```
⚠ Deprecated .env settings detected:
  ⚠ MESSAGING_CWD=/config/addons_data/hermes-agent/workspace found in .env
    — this is deprecated.
  Move to config.yaml instead:  terminal:\n    cwd: /your/project/path
```

Non-fatal, but future Hermes releases may start rejecting the variable
outright.

**Root cause**
Hermes v0.10.0 migrated the working-directory configuration from the
legacy `MESSAGING_CWD` env var to a dedicated `terminal.cwd` key in
`config.yaml`. Our `run.sh` was writing both — `.env` (legacy) AND
`config.yaml` (new). The legacy write was left over from the v0.9.x era
and no longer needed.

**Fix**
- Replaced `env_map["MESSAGING_CWD"] = str(messaging_cwd)` with
  `env_map.pop("MESSAGING_CWD", None)` — actively strips the value from
  existing `.env` files on upgrade, doesn't just stop writing it.
- The value is still written to `config.yaml` as `terminal.cwd`, which is
  where v0.10.0 reads it from.
- ttyd still needs `MESSAGING_CWD` in the bash environment to `cd` into
  the user's workspace on terminal launch. Rather than pollute Hermes's
  `.env`, we write it to `${HERMES_HOME}/.addon-runtime`, which `run.sh`
  sources after `.env`. This keeps the variable in the add-on's shell
  context without tripping Hermes's deprecation check.

**Invariants**
- Never reintroduce `MESSAGING_CWD` to `env_map` — it will regress the
  warning.
- If upstream eventually hard-errors on the variable, remove the
  `.addon-runtime` fallback too and have ttyd read `terminal.cwd` from
  `config.yaml` instead (e.g. via `yq`).

### v0.9.11 — Wrong default model + panel boot 502

Shipped: 2026-04-15. Upstream still `v2026.4.13 / v0.9.0`
(`sha256:0ee58988876f5bb3d6e8e664542bbad2eb9453b9f8ef9a669afc87316087b357`).

#### Fix 1 — Default model changed from `NousResearch/Hermes-4-14B` → `gpt-5.4`

**Symptom**
User opens the ttyd terminal, types any message. Hermes starts, then prints:

```
⚠  Nous Research Hermes 3 & 4 models are NOT agentic and are not designed
   for use with Hermes Agent. They lack tool-calling capabilities required
   for agent workflows.

⚠️  Stripped provider prefix from 'NousResearch/Hermes-4-14B';
    using 'Hermes-4-14B' for OpenAI Codex.
❌ HTTP 400: "The 'Hermes-4-14B' model is not supported when using Codex
   with a ChatGPT account."
```

Every chat turn 400s in the first call. Reproducible from a clean install.

**Root cause**
Historical naming collision. Nous Research publishes a family of open-weight
LLMs called "Hermes" (Hermes-4-14B, Hermes-4-70B, Hermes-4.3-36B, …). A
*separate* upstream project called "Hermes Agent" — maintained by
`nousresearch/hermes-agent` — is a general-purpose agent framework that
needs tool-calling-capable models (Claude, GPT, Gemini, DeepSeek, Grok).

v0.8.0 of this add-on was built under the wrong assumption that "Hermes
Agent" = "shell for running Nous Research Hermes LLMs", so the default
model was set to `NousResearch/Hermes-4-14B`. That default persisted
through v0.9.10 without anyone noticing because most testing went through
the in-page chat shim, which happily proxied to HuggingFace Inference API.

In v0.9.11 the upstream gateway got stricter and started explicitly
warning about this combination at agent-init time, then rejecting the
model at the provider layer (Codex refuses anything that isn't a GPT
model). This cascaded into a 100% chat-failure rate for any user on the
default config paired with the web_login flow.

Meanwhile `run.sh` bootstrap's `model_cfg.setdefault(...)` meant upgrade
paths from v0.8.0–v0.9.10 could not self-heal: if `/data/config.yaml`
already had `model.default: NousResearch/Hermes-4-14B` from a prior boot,
`setdefault` preserved it forever.

**Fix**
Three layers, all in `run.sh` Python bootstrap + `config.yaml`:

1. **`config.yaml` default** — `llm_model: "NousResearch/Hermes-4-14B"`
   → `llm_model: "gpt-5.4"`. Fresh installs get a working pairing with
   the default `openai-codex` provider + ChatGPT-account web login.

2. **Active migration for existing users** — after reading
   `/data/config.yaml`, check `model.default` against a blocklist of
   non-agentic prefixes: `NousResearch/Hermes`, `Hermes-3`, `Hermes-4`.
   If matched, overwrite with `gpt-5.4` and log:
   ```
   [run.sh] MIGRATING model.default 'NousResearch/Hermes-4-14B' → 'gpt-5.4'
            (Hermes Agent requires agentic models; see CHANGELOG v0.9.11)
   ```
   Also resets `provider`/`base_url` to `openai-codex` if they were tied
   to the legacy HuggingFace/NousResearch shim.

3. **Block the HA option path too** — if the user explicitly sets
   `llm_model: "NousResearch/Hermes-4-14B"` in the add-on UI, we log a
   WARNING and still fall back to `gpt-5.4`. Rationale: better to work
   with a surprising model than to fail every turn silently.

`OPENAI_SHIM_MODEL` and `API_SERVER_MODEL_NAME` fallbacks updated to
`gpt-5.4`. `translations/en.yaml`, `README.md`, `DOCS.md`, `INSTALL.md`
rewritten to recommend agentic models (Claude 4.6, Gemini 2.5 Pro,
DeepSeek V3, Grok 4, gpt-5.4, gpt-4o, o3, o4-mini) and explicitly warn
against NousResearch Hermes 3/4, Llama/Mistral base.

**Invariants for future upgrades**
- Do NOT put any `NousResearch/Hermes-*` identifier back in the default
  `llm_model` or in any recommended-model list. The name collision is a
  trap; the upstream framework needs tool calling.
- If upstream Hermes Agent *ever* adds support for Nous Research Hermes
  models (unlikely — they'd need to train tool-calling variants), you
  can remove the migration block. Until then, keep it.
- Keep the migration block tolerant: it only rewrites `model.default`
  when the current value is clearly non-agentic. Do not broaden it to
  touch `provider` or `base_url` unless you've verified no one is using
  a custom OpenAI-compatible endpoint with a legacy model name.
- When updating the docs, write the agentic-model list in order of
  expected preference: GPT > Claude > Gemini > DeepSeek > Grok — this
  is the order that has working providers in `run.sh` bootstrap.

#### Fix 2 — `/panel/` 502 during Vite build window

**Symptom**
First click on the "Hermes Dashboard" button after a fresh add-on start
returns a blank 502 JSON error. Waiting ~60 seconds and clicking again
works fine. Add-on log shows:

```
[run.sh] hermes dashboard started (PID 14)
[Hermes UI] 172.30.32.2 - "GET /panel/ HTTP/1.1" 502 -
...
→ Building web UI...          ← Vite compiles the SPA; takes ~42s on aarch64
  ✓ Web UI built
  Hermes Web UI → http://127.0.0.1:9119
[Hermes UI] 172.30.32.2 - "GET /panel/ HTTP/1.1" 200 -
```

**Root cause**
`hermes dashboard` does not bind 9119 immediately on launch. It first
runs a Vite build to produce the SPA bundle, which takes 30–60 seconds
on aarch64 (HA Green / Home Assistant Yellow / Raspberry Pi 5 class).
During that window, any connection attempt to 9119 gets `ECONNREFUSED`
because nothing is listening yet. Our `_proxy_panel_http` mapped that
directly to a plain JSON 502, which looked like a hard failure even
though it's a transient startup race.

**Fix**
Two-layer retry in `_proxy_panel_http`:

1. **In-proxy retries** — up to 3 attempts with 0.7s delay between each
   on `ECONNREFUSED` / `ENOENT`. Papers over the typical case where the
   build just finished a moment ago.

2. **HTML fallback page** — if all retries exhaust and the request is a
   browser HTML GET (`Accept: text/html`, path ends in `/` or `.html`),
   serve `_PANEL_BOOT_PAGE`: a small Chinese page with
   `<meta http-equiv="refresh" content="4">` that auto-reloads every
   4 seconds. Once the build finishes on the next refresh the user
   transparently lands on the real panel.

3. **SPA fetch/XHR still get JSON 502** — distinguished by the Accept
   header and the path shape. This is important: the SPA has its own
   retry logic and doesn't want an HTML body as a JSON response.

**Invariants for future upgrades**
- If upstream starts pre-building the Vite bundle at image build time
  (so 9119 binds instantly), the retry/boot-page logic becomes dead
  code but is harmless — leave it as insurance against regressions.
- Do not extend the retry count or delay much. HA Ingress aiohttp has
  a request timeout; blocking for 10+ seconds in a single HTTP handler
  risks the Supervisor killing the connection.
- The boot page must stay tiny. No JS, no external fonts, no external
  assets. It's served *precisely* when the network is flaky.

---

### v0.9.10 — Adopt upstream web dashboard + terminal PATH + launcher UI

Shipped: 2026-04-15. Upstream still `v2026.4.13 / v0.9.0`
(`sha256:0ee58988876f5bb3d6e8e664542bbad2eb9453b9f8ef9a669afc87316087b357`).

This release bundles **three independent fixes** driven by the v2026.4.13
upstream upgrade. Keep them separate mentally — each has its own root cause
and its own regression surface.

#### Fix 1 — `/panel/**` reverse proxy to `hermes dashboard`

**Symptom**
Nothing was broken per se. Hermes v2026.4.13 (v0.9.0) ships a brand-new
`hermes dashboard` FastAPI-based local web UI, but the HA add-on had no way
to surface it through Ingress (single-port, path-prefixed). Users asked
"there's a web panel now, how do I open it?" and the answer was "you can't".

**Root cause**
Home Assistant Ingress only exposes one port per add-on (`ingress_port:
8099`). `hermes dashboard` listens on `127.0.0.1:9119` by default. Without a
proxy, port 9119 is reachable only from inside the container — the browser
can never hit it.

**Fix**
Three-layer bridge:

1. **`run.sh` step 5b** — start `hermes dashboard --host 127.0.0.1 --port
   9119 --no-open &` in the background. Guarded with `--help` probe so older
   Hermes builds without the subcommand skip this step rather than aborting.
2. **`server.py` `/panel/**`** — new `_proxy_panel_http` and
   `_proxy_panel_websocket` methods modelled on the existing ttyd proxy.
   Strips the `/panel` prefix before forwarding. WebSocket upgrade
   handshake is raw-byte relayed after a 101 response from upstream.
3. **JS + HTML rewriting** — FastAPI SPAs use absolute asset paths
   (`<script src="/assets/foo.js">`) and runtime absolute URLs
   (`fetch("/api/bar")`). Neither resolves correctly under HA Ingress.
   `_rewrite_panel_html` replaces `href="/x"` / `src="/x"` / `action="/x"`
   with `href="./x"` etc. using a compiled regex, and injects a
   `_PANEL_JS_PATCH` script into `<head>` that wraps `window.fetch`,
   `XMLHttpRequest.prototype.open`, and `window.WebSocket`. The wrapper
   computes `PANEL_BASE` from `window.location.pathname` (everything up to
   and including `/panel`) and prepends it to any absolute-path URL that
   isn't already under the panel base.

**Invariants for future upgrades**
- If upstream changes `hermes dashboard`'s default port away from 9119,
  update `HERMES_PANEL_PORT` in `Dockerfile`, `run.sh`, and `server.py`
  in the same commit.
- If upstream drops `hermes dashboard` or renames the subcommand, the
  `if /opt/hermes/.venv/bin/hermes dashboard --help` probe in `run.sh`
  logs a warning and the proxy returns 502 cleanly — not a crash.
- Do NOT remove the defensive `pip install fastapi uvicorn[standard]`
  line in `Dockerfile`. It's a safety net for offline / partial-layer
  builds where the upstream image ships without the `web` extra.
- FastAPI uses PUT/PATCH verbs. `server.py` now has `do_PUT` and
  `do_PATCH` dispatchers that route to `/panel/**` and `/api/**`. Don't
  delete them when refactoring method handling.

#### Fix 2 — `hermes` command not found inside ttyd terminal

**Symptom**
Opening the ttyd terminal (Hermes UI → 终端 button) and typing `hermes`
returned `bash: hermes: command not found`, even though the Hermes gateway
was clearly running and the venv existed at `/opt/hermes/.venv/`.

**Root cause**
`run.sh` started ttyd with `/bin/bash -lc ...`. The `-l` flag makes bash
run `/etc/profile` on startup. On Debian, `/etc/profile` unconditionally
resets `PATH` to the hard-coded default:

```
/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

This clobbered the `PATH=/opt/hermes/.venv/bin:$PATH` that `run.sh` step 1
had exported, so `hermes` (which lives at `/opt/hermes/.venv/bin/hermes`)
fell off the lookup path inside the terminal session. The gateway process
was unaffected because it was launched directly by `run.sh` with the
un-clobbered PATH — only shells spawned by ttyd lost it.

**Fix (two layers)**
1. **`/etc/profile.d/hermes.sh`** (baked into the image by `Dockerfile`) —
   runs *after* `/etc/profile` inside login shells and re-adds
   `/opt/hermes/.venv/bin` to `PATH` (plus re-exports `HERMES_HOME` and
   `HERMES_INSTALL_DIR` as a belt-and-suspenders). Idempotent: uses a
   `case ":$PATH:"` check so it doesn't keep appending on repeated sourcing.
2. **`run.sh` ttyd launch** — changed `/bin/bash -lc` → `/bin/bash -c`
   (drop the `-l` flag). This skips `/etc/profile` entirely so the venv
   PATH inherited from `run.sh`'s own environment survives into the
   interactive shell.

**Invariants for future upgrades**
- Do not re-add `-l` to the ttyd bash invocation in `run.sh`. If you need
  login-shell behaviour for some reason, rely on the profile.d drop-in
  instead.
- If the upstream Hermes image starts shipping its own `/etc/profile.d`
  entry that sets `PATH`, the ordering may conflict. Verify by running
  `echo $PATH` in the ttyd terminal after upgrading and make sure
  `/opt/hermes/.venv/bin` is still present.

#### Fix 3 — Web UI slimmed to 2-button launcher

**Symptom**
The v0.9.9 UI had a sidebar with OpenAI Codex login bridge, a chat
composer, prompt buttons, a transcript, and a terminal card — all
competing for attention. Users just wanted to launch the official
dashboard or open a terminal. The in-page chat duplicated functionality
that the upstream dashboard now does better.

**Root cause**
Legacy UX from before v2026.4.13 had `hermes dashboard`. We built our own
chat surface because upstream had none. Now that upstream ships a real
dashboard, the in-page chat is redundant and dilutes the primary entry
points.

**Fix**
Full `index.html` rewrite as a **launcher**. Only retains:
- Brand block + tagline
- Status strip (model, gateway health, ingress port, add-on version)
- Two large cards: "Hermes Dashboard" → `./panel/`, "Hermes 终端" → `./ttyd/`
- Footer note about ingress routing

`app.js` dropped from 713 lines → ~140 lines. Only `loadModels()` and
`checkHealth()` survive (plus the error banner handler). Everything else —
auth bridge, chat composer, prompt history, conversation UUID, thinking
placeholder — was removed. Legacy CSS is retained at the top of
`styles.css` as dead code so an old cached `index.html` still renders.
New launcher styles live in a clearly marked block at the bottom.

**Invariants for future upgrades**
- Do not add new features to the launcher page. If users ask for chat or
  config management, direct them to the official `/panel/` dashboard.
- The launcher must work with JavaScript disabled — all visible text is
  pre-rendered in `index.html` Chinese literals. `app.js` only *updates*
  the model name and health pill from `/config-model` and `/health`.
- Keep `js-error-banner` and the `onerror` handler — they are the only
  way to surface JS failures to end users who don't check devtools.

---

### v0.9.9 — `HERMES_HOME` hardcoded in upstream `entrypoint.sh`

**Symptom**
Every chat request returned `Invalid API key` after an add-on restart, even
though `hermes auth login openai-codex` from the ttyd terminal had just
written valid OAuth tokens to `/data/auth.json` seconds earlier. Status
card showed the correct model. `curl http://127.0.0.1:8642/v1/models` worked.
But `POST /v1/chat/completions` failed auth.

**Root cause**
`run.sh` step 6 was `exec /opt/hermes/docker/entrypoint.sh gateway run`.
The upstream entrypoint starts with:

```bash
export HERMES_HOME=/opt/data
```

This **clobbered** the `HERMES_HOME=/data` that `run.sh` step 1 had exported.
The running `hermes gateway` process therefore looked up `auth.json`,
`config.yaml`, and `.env` in `/opt/data/` — an ephemeral container
directory that (a) did not contain the files we wrote to `/data/` and
(b) was wiped every time the container was recreated.

The reason this bug was so sticky: `hermes` CLI commands run from inside
ttyd **inherited the user shell's env** (which had our `/data`), so
`hermes auth login` wrote tokens to the correct place — but the gateway
process, started via the upstream entrypoint, was reading from the wrong
place. Authentication therefore always appeared to succeed interactively
and always failed from the UI.

**Fix** (in `run.sh`)
```bash
# Manually replicate the one upstream bootstrap we still need
if [ -f "${HERMES_INSTALL_DIR}/tools/skills_sync.py" ]; then
  python3 "${HERMES_INSTALL_DIR}/tools/skills_sync.py" || true
fi

# Symlink fallback so older Hermes releases that still look in /opt/data
# keep working without regenerating state.
if [ -d /opt/data ]; then
  for f in auth.json config.yaml .env SOUL.md; do
    [ -e "/opt/data/$f" ] && [ ! -L "/opt/data/$f" ] && rm -f "/opt/data/$f"
    [ -e "/data/$f" ] && ln -sf "/data/$f" "/opt/data/$f" 2>/dev/null || true
  done
fi

exec hermes gateway run   # <-- direct exec, bypassing entrypoint.sh
```

**Do not revert** until you have confirmed upstream no longer hardcodes
`HERMES_HOME`. Test with:
```bash
docker exec <addon> cat /proc/$(pgrep -f 'hermes gateway')/environ \
  | tr '\0' '\n' | grep HERMES_HOME
# Expect: HERMES_HOME=/data
```

---

### v0.9.9 — `LLM_MODEL` env var removed in v2026.4.13

**Symptom**
After upgrading to Hermes v2026.4.13, the gateway used the wrong model
regardless of what the HA option `llm_model` was set to. Old `.env` files
from pre-v2026.4.13 still had `LLM_MODEL="NousResearch/Hermes-4-14B"`.

**Root cause**
Upstream v2026.4.13 removed the `LLM_MODEL` env var. Model selection is
now **only** read from `config.yaml` → `model.default`. Old `.env` files
carried a stale `LLM_MODEL=` line that was now a no-op, and `run.sh` was
still writing it on every boot.

**Fix** (`run.sh` Python bootstrap)
```python
# Don't set LLM_MODEL at all — upstream removed it in v2026.4.13.
# Strip any stale value that an old .env might still carry.
env_map.pop("LLM_MODEL", None)
```
Model is now written only to `/data/config.yaml`:
```python
model_cfg = config.get("model") or {}
if llm_model:
    model_cfg["default"] = llm_model
model_cfg.setdefault("provider", "openai-codex")
model_cfg.setdefault("base_url", "https://chatgpt.com/backend-api/codex")
config["model"] = model_cfg
```

---

### v0.9.9 — `model:` must be a dict in `config.yaml`

**Symptom**
`hermes gateway` failed to start with a YAML validation error on first
boot after upgrading to v2026.4.13.

**Root cause**
`config.yaml` schema changed: `model:` used to accept a bare string, now
must be a mapping with `default`, optional `provider`, optional `base_url`.
`run.sh` was still writing `config["model"] = llm_model`.

**Fix**
See the snippet above — `run.sh` now always writes `model` as a dict and
preserves existing keys.

---

### v0.9.9 — `generateUUID()` infinite recursion in secure contexts

**Symptom**
When the add-on was accessed over HTTPS or `localhost`, the chat UI never
initialized. Browser console showed `RangeError: Maximum call stack size
exceeded`.

**Root cause**
`hermes_ui/app.js`:
```js
function generateUUID() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return generateUUID();  // <-- calls itself, stack overflow
  }
  ...
}
```
The secure-context branch was supposed to call the native
`crypto.randomUUID()` but instead called back into itself.

**Fix**
```js
return crypto.randomUUID();
```

---

### v0.9.9 — Sidebar auth panel replaced with model card

**Symptom**
The sidebar had a large OpenAI Codex login panel, but the actual `hermes
auth login openai-codex` flow must run in the ttyd terminal (the in-page
bridge was a historical experiment that never graduated). The panel
confused users into trying to authenticate from the wrong place.

**Fix**
- Removed the auth panel from `index.html`.
- Kept hidden legacy DOM nodes (`auth-pill`, `auth-start`, etc.) so
  `app.js`'s `applyAuthStatus` / `attachAuthHandlers` don't `ReferenceError`.
- Added a new sidebar card that displays the **real** running model via a
  new `/config-model` endpoint in `server.py`, which reads
  `/data/config.yaml` directly and returns `{model, provider}`.
- `loadModels()` in `app.js` prefers `/config-model`; falls back to
  `/models` (proxy to gateway `/v1/models`) if unavailable.

---

### v0.9.8 — ttyd HTTP 502 via gzip Content-Length mismatch

**Symptom**
`/ttyd/` intermittently returned 502 Bad Gateway after the ttyd HTML
response started including gzip encoding.

**Root cause**
`_proxy_ttyd_http` forwarded the client's `Accept-Encoding: gzip` header
upstream. Upstream ttyd returned `Content-Encoding: gzip` + compressed
body. Our proxy copied the header through, but also separately set
`Content-Length` to the **uncompressed** length, creating a mismatch that
HA's nginx front-end terminated with 502.

**Fix**
Strip `Accept-Encoding` from forwarded request headers, force
`Accept-Encoding: identity`, and strip `Content-Encoding` from the
response headers we return.

---

### v0.9.7 — ttyd `/ttyd/token` fetched over host, bypassing Ingress

**Symptom**
Terminal panel loaded but WebSocket connection failed with 401/404.

**Root cause**
ttyd's JS fetches `http://HOST:8123/ttyd/token` over the raw host (not
through HA Ingress), which returns 404 because HA doesn't route that
path externally.

**Fix**
Inject a JS patch into the ttyd HTML response that wraps `window.fetch`,
`XMLHttpRequest.open`, and `window.WebSocket` so `/ttyd/token` becomes a
relative `./token` request that flows through our `server.py` proxy
(and therefore HA Ingress).

---

### v0.9.6 / v0.9.5 — ttyd WebSocket URL rewriting

**Symptom**
Terminal WebSocket failed with 502 even after fixing the token endpoint.

**Root cause**
ttyd's JS built WebSocket URLs from `window.location.host + "/ttyd/ws"`,
which omitted the HA Ingress token path. HA nginx had no matching route
and returned 502.

**Fix**
- v0.9.5: rewrote `_proxy_ttyd_websocket` to be a real WS proxy and return
  proper HTTP 502 on upstream failure (rather than trying to write HTTP on
  an already-upgraded WS connection).
- v0.9.6: injected JS that rewrites `/ttyd/ws` WebSocket URLs to be
  relative to the current page (so the Ingress token prefix is preserved).

---

### v0.9.4 — Missing `Content-Length` on all responses

**Symptom**
All proxied responses from `server.py` intermittently returned 502 from HA.

**Root cause**
`_proxy_ttyd_http`, `_serve_file`, `_send_json`, and `_send_html` were
dropping upstream `Transfer-Encoding: chunked` without setting an explicit
`Content-Length`. HA nginx couldn't determine the end of the response.

**Fix**
All response helpers now buffer and set `Content-Length: N`.

---

### v0.9.3 — `crypto.randomUUID` missing in HTTP contexts

**Symptom**
UI wouldn't initialize when accessed over plain HTTP on LAN.

**Root cause**
`crypto.randomUUID()` is only defined in secure contexts (HTTPS or
`localhost`). HA LAN access over plain HTTP lacks it.

**Fix**
Added `generateUUID()` polyfill that uses `crypto.getRandomValues()`. (The
recursion bug in the secure-context branch was later discovered and fixed
in v0.9.9, see above.)

---

### v0.9.2 — Gateway `Connection Refused` under HA user isolation

**Symptom**
UI showed gateway unreachable. `curl http://127.0.0.1:8642/...` from inside
the container worked, but not from the gateway's own user-auth layer.

**Root cause**
Hermes gateway defaults to an allowlist of approved user IDs. HA's
add-on container doesn't have user identities the way the upstream
expects.

**Fix**
`run.sh` now sets `GATEWAY_ALLOW_ALL_USERS=true` — we trust HA Ingress to
handle external auth, and the gateway is loopback-only.

---

### v0.9.1 — `ttyd` binary at `/usr/bin/ttyd` not `/usr/local/bin/ttyd`

**Symptom**
`run.sh` silently failed to start ttyd; terminal panel 502'd.

**Root cause**
`apt-get install ttyd` from Debian sid installs to `/usr/bin/ttyd`, but
`run.sh` had the path hardcoded.

**Fix**
`TTYD_BIN="$(command -v ttyd)"` — resolve at runtime from PATH.

---

## Lessons / invariants to preserve

1. **Never reintroduce a call to `/opt/hermes/docker/entrypoint.sh`** from
   `run.sh` until the upstream stops hardcoding `HERMES_HOME=/opt/data`.
2. **Never set `LLM_MODEL` in `.env`.** Model selection lives in
   `config.yaml` only. `run.sh` must actively strip stale entries.
3. **Every new HTTP response helper in `server.py` must set
   `Content-Length`** or HA's nginx front-end will 502.
4. **Never forward `Accept-Encoding` upstream** in the ttyd HTTP proxy —
   we serve the body verbatim so it must be uncompressed.
5. **ttyd client JS must always be patched** to route `/token` fetches
   and `/ws` WebSocket upgrades through relative URLs (so HA Ingress token
   prefix is preserved).
6. **Pin the upstream image by sha256 digest**, not tag. Tags move.
7. **Test a full container recreation**, not just a restart — state bugs
   only show up when the writable layer is wiped.
