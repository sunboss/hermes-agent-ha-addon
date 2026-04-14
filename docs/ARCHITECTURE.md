# Architecture & State Layout

> This document is written so that a **future human maintainer or AI agent
> picking up this repo cold** can quickly understand how the pieces fit
> together, where persistent state lives, and — critically — the landmines
> that have historically broken this add-on. When upgrading, **read this
> before touching `run.sh` or `Dockerfile`**.

---

## 1. What the add-on is

A Home Assistant add-on that wraps the upstream
[`nousresearch/hermes-agent`](https://hub.docker.com/r/nousresearch/hermes-agent)
Docker image and exposes:

1. A chat Web UI over **HA Ingress** (port `8099`).
2. A full `ttyd`-based terminal under `./ttyd/` (for `hermes auth login`, etc.).
3. A proxy to the Hermes OpenAI-compatible API server at `127.0.0.1:8642`.

HA Ingress is the **only** external access path — the gateway itself is
always bound to loopback.

## 2. Process tree inside the container

```
/run.sh (PID 1, bash)
├── ttyd (background)               # port 7681, served under /ttyd/
├── python3 server.py (background)  # port 8099, HA Ingress entrypoint
└── hermes gateway run (foreground) # port 8642, loopback only
```

`run.sh` starts all three. When `hermes gateway run` exits, the container
exits — that is what keeps `hermes` as the main process for supervisor.

## 3. Where state lives — the `/data` vs `/opt/data` trap

This is the **single most important thing** to understand about this repo.
Almost every "it worked, then a restart broke it" bug has traced back here.

| Path                     | Persistence      | What lives there               |
| ------------------------ | ---------------- | ------------------------------ |
| `/data/`                 | **HA data volume (persistent across restarts & upgrades)** | `auth.json`, `config.yaml`, `.env`, `SOUL.md`, `sessions/`, `workspace/`, `auth/session.json`, `options.json` |
| `/opt/data/`             | **Container writable layer (wiped on every container recreation)** | Leftover from upstream entrypoint — must **NOT** be used |
| `/opt/hermes/`           | Image (read-only in practice) | Upstream Hermes install, `.venv`, `docker/entrypoint.sh`, `tools/skills_sync.py` |
| `/opt/hermes-ha-ui/`     | Image (baked at build) | `server.py`, `app.js`, `index.html`, `styles.css` |

**The landmine:** the upstream image ships
`/opt/hermes/docker/entrypoint.sh` with `export HERMES_HOME=/opt/data`
**hardcoded at the top of the script**. If `run.sh` ever calls that
entrypoint — even via `exec /opt/hermes/docker/entrypoint.sh gateway run` —
that export clobbers our `HERMES_HOME=/data`, and the gateway reads
`auth.json` / `config.yaml` / `.env` from `/opt/data`, which:

1. Does not have the files we just wrote to `/data`.
2. Gets wiped every time the container is recreated.

Symptoms when this happens:
- "Invalid API key" on every chat request, *even though* `hermes auth login`
  appeared to succeed moments earlier.
- OAuth tokens / config / skills mysteriously disappearing after an add-on
  restart or upgrade.
- `hermes` CLI commands from inside ttyd work, but gateway requests from the
  UI don't — because `hermes` CLI inherits the user's env (our `/data`),
  while the gateway inherited the upstream entrypoint's env (`/opt/data`).

**The fix (currently in `run.sh`):**
```bash
# Replicate the one upstream bootstrap step we actually need...
if [ -f "${HERMES_INSTALL_DIR}/tools/skills_sync.py" ]; then
  python3 "${HERMES_INSTALL_DIR}/tools/skills_sync.py" || true
fi

# ...and exec hermes directly, bypassing upstream entrypoint.sh entirely.
exec hermes gateway run
```

Plus a safety net that symlinks `/opt/data/{auth.json,config.yaml,.env,SOUL.md}`
to their `/data/` counterparts, so an older Hermes release that still
looks in `/opt/data` keeps working.

**Do not revert this** unless the upstream entrypoint stops hardcoding
`HERMES_HOME`. Always verify with:
```bash
docker exec <addon> env | grep HERMES_HOME    # must show /data
docker exec <addon> pgrep -a hermes            # gateway should be child of /run.sh
docker exec <addon> cat /proc/$(pgrep -f 'hermes gateway')/environ | tr '\0' '\n' | grep HERMES_HOME
```

## 4. URL routing (HA Ingress → server.py → backends)

```
HA Ingress (browser)
      │
      ▼
server.py on :8099
      │
      ├── /                     → serve index.html
      ├── /app.js, /styles.css  → serve static files
      ├── /health               → local liveness + gateway ping
      ├── /models               → proxy GET http://127.0.0.1:8642/v1/models
      ├── /config-model         → read /data/config.yaml directly (added v0.9.9)
      ├── /api/**               → proxy to http://127.0.0.1:8642/**
      ├── /auth/**              → local PKCE state machine (auth_bridge.py)
      ├── /ttyd/                → HTTP → ttyd, rewrite HTML to inject WS patch
      ├── /ttyd/ws              → WebSocket upgrade → ttyd
      └── /ttyd/token           → fetch intercept → ttyd (same-origin via Ingress)
```

The `/ttyd/token` redirect (via injected JS in the ttyd HTML) is important:
ttyd's default JS calls `fetch('http://HOST:8123/ttyd/token')` over the
**host**, bypassing HA Ingress, which returns 404. We rewrite that call to
a relative `./token` so it flows through our proxy.

## 5. Key files and what each one is for

### Build-time
- `hermes_agent/Dockerfile` — pins upstream image via `sha256` digest.
  Update `HERMES_IMAGE_DIGEST`, not tags, so builds are reproducible.
- `hermes_agent/config.yaml` — HA add-on manifest (version, schema, options).
- `hermes_agent/build.yaml` — base image for multi-arch builds.

### Runtime entrypoint
- `hermes_agent/run.sh` — the **one** entrypoint. Reads `/data/options.json`,
  patches `/data/.env` and `/data/config.yaml`, starts ttyd + server.py, then
  `exec hermes gateway run`. Contains the HERMES_HOME landmine comment.

### Ingress Web UI
- `hermes_agent/hermes_ui/server.py` — Python `http.server` with WebSocket
  upgrade support. Proxies `/api/**` to the gateway, handles `/auth/**`
  locally, rewrites `/ttyd/` HTML. Also now serves `/config-model`.
- `hermes_agent/hermes_ui/auth_bridge.py` — PKCE OAuth state machine for
  `auth_mode=web_login`. Persists state to `/data/auth/session.json`.
- `hermes_agent/hermes_ui/provider_shim.py` — OpenAI-compatible shim for
  the web-login flow.
- `hermes_agent/hermes_ui/{index.html,styles.css,app.js}` — the chat UI.
- `hermes_agent/hermes_ui/{terminal.html,terminal.css,terminal.js}` — the
  full-screen ttyd shell.

## 6. `config.yaml` format after v2026.4.13

`model:` must be a **mapping**, not a plain string:

```yaml
model:
  default: gpt-5.4
  provider: openai-codex          # or: huggingface | openrouter | openai | ...
  base_url: https://chatgpt.com/backend-api/codex
```

`run.sh` writes this automatically based on the `llm_model` HA option.
The `LLM_MODEL` env var was removed in v2026.4.13 — do not set it, do not
expect Hermes to read it, and `run.sh` actively `pop()`s it from stale
`.env` files on startup.

## 7. Common pitfalls checklist (for future upgrades)

When bumping the upstream Hermes image, verify each of the following before
shipping:

- [ ] `HERMES_HOME` inside the running gateway process is `/data` (see §3).
- [ ] `/data/auth.json` survives an add-on restart.
- [ ] `/data/config.yaml` still has `model:` as a **dict**, not a string.
- [ ] `LLM_MODEL` is **not** present in `/data/.env` after restart.
- [ ] `hermes auth login openai-codex` from ttyd writes to `/data/auth.json`
      (not `/opt/data/auth.json`).
- [ ] `curl http://127.0.0.1:8099/config-model` returns the real model name.
- [ ] `curl http://127.0.0.1:8099/models` proxies through to gateway `/v1/models`.
- [ ] `/ttyd/` loads without a 502 (check the injected JS patch still applies
      to whatever ttyd version Debian unstable is shipping).
- [ ] Upstream `docker/entrypoint.sh` has **not** gained new bootstrap steps
      that `run.sh` now also needs to replicate.
