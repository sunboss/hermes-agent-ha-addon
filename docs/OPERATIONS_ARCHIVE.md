# Operations Archive

This is the maintenance entrypoint for `sunboss/hermes-agent-ha-addon`.
Keep public process notes here, and keep secrets only in the local ignored
file `.ops/secrets.local.md`.

## Current Release State

- Repository: `https://github.com/sunboss/hermes-agent-ha-addon`
- Add-on version: `2026.6.21.0`
- Upstream image: `nousresearch/hermes-agent:v2026.6.19`
- Upstream release: Hermes Agent `v0.17.0`, release date `2026-06-19`
- Local checkout: `/Users/sunboss/Documents/hermes/hermes-agent-ha-addon`

## Local Secret Archive

Use this path for passwords, API keys, GitHub tokens, Home Assistant tokens,
Docker credentials, and one-off recovery codes:

```text
.ops/secrets.local.md
```

That file is intentionally ignored by Git. Do not commit it, paste it into
issues, or push it to GitHub. If a token must be shared with another machine,
copy it through a password manager or an encrypted channel.

Create it from the template:

```bash
cp .ops/secrets.local.md.example .ops/secrets.local.md
chmod 600 .ops/secrets.local.md
```

## Upgrade Checklist

1. Read `docs/ARCHITECTURE.md` and `docs/UPGRADE_LOG.md`.
2. Check upstream release notes for Docker, gateway, dashboard, config, and
   Home Assistant platform changes.
3. Confirm Docker Hub has an explicit date tag:
   `https://hub.docker.com/r/nousresearch/hermes-agent/tags`.
4. Update these files together:
   - `hermes_agent/Dockerfile`
   - `hermes_agent/config.yaml`
   - `hermes_agent/hermes_ui/version.json`
   - `README.md`
   - `hermes_agent/CHANGELOG.md`
   - `docs/UPGRADE_LOG.md`
5. Run local checks:
   - `bash -n hermes_agent/run.sh`
   - `python3 -m py_compile` for wrapper Python files
   - YAML parse check for add-on YAML files
6. Build in Home Assistant or Docker and verify:
   - Gateway starts without root refusal
   - `/health` reports UI alive
   - `/panel/` loads the upstream dashboard
   - `/ttyd/` opens a terminal in `/config/workspace`
   - Home Assistant WebSocket connects through `/core/websocket`
7. Commit, push, and record the result in this file or `docs/UPGRADE_LOG.md`.

## Push Checklist

```bash
git status --short
git diff --check
git add .
git commit -m "Fix v2026.6.19 s6 entrypoint startup"
git push origin main
```

Before pushing, confirm `.ops/secrets.local.md` is not staged:

```bash
git status --short --ignored .ops
```

## Rollback Notes

If `v2026.6.19` fails on a Home Assistant host:

1. Revert `BUILD_FROM` in `hermes_agent/Dockerfile` to
   `nousresearch/hermes-agent:v2026.5.16`.
2. Revert add-on version metadata to the last working release.
3. Keep the `gosu hermes` privilege-drop fix unless it is proven to be the
   direct cause. It is compatible with the official image layout and prevents
   root-owned persistent files.
4. Rebuild the add-on from the HA UI.

## Operation Log

### 2026-06-21 — Fixed `v2026.6.19` s6 entrypoint loop

**Context.** HAOS rebuilt the `2026.6.20.0` add-on and the container entered a
restart loop after upstream s6 cont-init completed. The decisive log line was:

```text
/run/s6/basedir/scripts/rc.init: 91: -g: not found
```

**Cause.** Upstream `v2026.6.19` ships `/usr/bin/tini` as a symlink to s6
`/init`. The add-on's old `ENTRYPOINT ["/usr/bin/tini", "-g", "--",
"/run.sh"]` therefore passed legacy tini flags into s6. s6 then tried to run
`-g` as a command.

**Fix prepared in `2026.6.21.0`.**

- Keep upstream image pinned to `nousresearch/hermes-agent:v2026.6.19`.
- Change Docker ENTRYPOINT to direct `/run.sh`.
- Keep the existing root config render, `gosu hermes`, Dashboard/UI/ttyd, and
  gateway startup order.

### 2026-06-20 — Prepared upstream `v2026.6.19` upgrade

**Context.** Upstream GitHub latest release is Hermes Agent `v0.17.0`
(`v2026.6.19`, release date 2026-06-19). Docker Hub exposes an explicit
multi-architecture `nousresearch/hermes-agent:v2026.6.19` tag, so this release
can keep the repository's fixed calendar-tag policy.

**Prepared add-on release.**

- Add-on version: `2026.6.20.0`
- Upstream image: `nousresearch/hermes-agent:v2026.6.19`
- Prior known-good rollback image: `nousresearch/hermes-agent:v2026.5.16`

**Risk focus for HAOS verification.**

- Preserve the `2026.5.20.0` root-then-drop ordering around
  `/data/options.json`.
- Verify upstream still includes `gosu` and `hermes dashboard`; do not use
  `/usr/bin/tini` on `v2026.6.19+` because it is an s6 `/init` symlink.
- Verify the Ingress wrapper, Dashboard proxy, ttyd, and gateway all start
  after HAOS rebuild.

### 2026-05-20 — HAOS startup verification for `2026.5.20.0`

**Context.** `2026.5.19.0` upgraded the add-on to upstream
`nousresearch/hermes-agent:v2026.5.16` and introduced privilege dropping to
avoid upstream's official-image root gateway guard. HAOS logs showed two
distinct failures before the final fix landed:

1. Before privilege dropping:

   ```text
   [run.sh] Starting Hermes Agent gateway (HERMES_HOME=/config/.hermes)...
   Hermes Web UI -> http://127.0.0.1:9119
   Refusing to run the Hermes gateway as root inside the official Docker image.
   ```

2. After dropping privileges too early:

   ```text
   [run.sh] Dropping root privileges to hermes (HERMES_HOME=/config/.hermes)...
   PermissionError: [Errno 13] Permission denied: '/data/options.json'
   ```

**Fix shipped in `2026.5.20.0`.** `run.sh` now renders config from
`/data/options.json` as root, then `chown`s `/config`, then re-execs itself as
`hermes`. The second pass skips configuration rendering with
`HERMES_ADDON_CONFIGURED=1`.

**Successful HAOS signal.** The verified startup log now contains:

```text
[run.sh] Dropping root privileges to hermes (HERMES_HOME=/config/.hermes)...
[Hermes UI] Listening on http://0.0.0.0:8099
[run.sh] Starting hermes dashboard on 127.0.0.1:9119...
[run.sh] hermes dashboard started
Syncing bundled skills into ~/.hermes/skills/ ...
Done: 2 new, 77 updated, 8 unchanged, 4 cleaned from manifest. 87 total bundled.
[run.sh] Starting Hermes Agent gateway (HERMES_HOME=/config/.hermes)...
Hermes Gateway Starting...
```

This confirms the root refusal and `/data/options.json` permission failure are
resolved.

**Non-fatal warnings observed.**

- `No watch_domains, watch_entities, or watch_all configured`: expected when
  no HA entity filters are configured. Set `watch_all: true` or configure
  `watch_domains` / `watch_entities` if Hermes should react to HA state
  changes.
- `WEIXIN_GROUP_POLICY=open...`: upstream Hermes warning about iLink WeChat
  group delivery limitations. It does not affect HA add-on startup.

**Maintenance note.** Keep this order in future `run.sh` changes:

1. Root: create `/config` dirs.
2. Root: run `configure.py` while `/data/options.json` is readable.
3. Root: `chown -R hermes:hermes /config`.
4. `gosu hermes`.
5. Hermes user: start ttyd, Ingress UI, dashboard, skills sync, and gateway.

### 2026-05-20 — Dashboard traffic and gateway restart verification

**Observed traffic.** HAOS logs showed repeated successful dashboard and
terminal checks:

```text
[Hermes UI] 172.30.32.2 - "GET /health HTTP/1.1" 200 -
[Hermes UI] 172.30.32.2 - "GET /panel/api/sessions?limit=50&offset=0 HTTP/1.1" 200 -
[Hermes UI] 172.30.32.2 - "GET /panel/api/status HTTP/1.1" 200 -
[Hermes UI] 172.30.32.2 - "HEAD /panel/ HTTP/1.1" 200 -
[Hermes UI] 172.30.32.2 - "HEAD /ttyd/ HTTP/1.1" 200 -
```

**Interpretation.** These are healthy Dashboard/Ingress polling requests, not
an error loop. `200` on `/health`, `/panel/api/status`, `/panel/api/sessions`,
`/panel/`, and `/ttyd/` means the UI wrapper, upstream dashboard proxy, and
terminal route are reachable.

**Gateway restart.** The dashboard sent:

```text
POST /panel/api/gateway/restart HTTP/1.1" 200
WARNING gateway.run: Shutdown context: signal=SIGTERM under_systemd=yes parent_pid=1 parent_name=tini
```

This is expected when the Dashboard asks the gateway to restart. The
This was valid for the pre-s6 upstream images. On `v2026.6.19+`, do not expect
`parent_name=tini`; `/run.sh` should be the direct entrypoint.

**Caution.** The Dashboard also exposes:

```text
POST /panel/api/hermes/update
```

Avoid using this as the normal HA add-on update path. HA add-ons should be
updated by bumping this repository, pushing to `main`, and using HAOS
Update/Rebuild so Dockerfile patches, add-on metadata, and wrapper scripts stay
in sync.
