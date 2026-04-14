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
