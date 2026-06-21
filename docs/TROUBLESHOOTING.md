# Troubleshooting

Fast symptom-to-cause lookup for Hermes Agent HA add-on maintenance.

## Gateway Refuses Root

Log:

```text
Refusing to run the Hermes gateway as root inside the official Docker image.
```

Cause:

Upstream Hermes v0.14.0 refuses root gateway startup in the official image.

Fix:

Use add-on `2026.5.20.0` or newer. `run.sh` must render config as root, then
drop to `hermes` before starting the gateway.

Do not permanently set:

```text
HERMES_ALLOW_ROOT_GATEWAY=1
```

## `/data/options.json` Permission Denied

Log:

```text
PermissionError: [Errno 13] Permission denied: '/data/options.json'
```

Cause:

The wrapper dropped to `hermes` before reading HA Supervisor options.

Fix:

Keep `configure.py` before `gosu hermes` in `run.sh`.

Required order:

1. root creates `/config` dirs.
2. root reads `/data/options.json` through `configure.py`.
3. root `chown`s `/config`.
4. `gosu hermes`.
5. services start as `hermes`.

## HAOS Does Not Detect Update

Check remote first:

```bash
curl -fsSL https://raw.githubusercontent.com/sunboss/hermes-agent-ha-addon/main/hermes_agent/config.yaml
```

If remote `version:` is correct, refresh HAOS:

```bash
ha store reload
ha supervisor reload
ha addons list | grep -i hermes
ha addons info <slug>
```

Likely causes:

- HAOS add-on store cache is stale.
- HAOS host cannot reach GitHub.
- Installed add-on came from a different repository URL.
- Version was not bumped in `hermes_agent/config.yaml`.

## Dashboard Works But Gateway Restarts

Log:

```text
POST /panel/api/gateway/restart HTTP/1.1" 200
WARNING gateway.run: Shutdown context: signal=SIGTERM ... parent_name=tini
```

Cause:

Dashboard requested a gateway restart. This is normal. On `v2026.6.19+`, the
parent name may no longer be `tini` because the add-on runs `/run.sh`
directly to avoid the upstream s6 `/init` shim.

Fix:

No fix needed unless the gateway fails to come back. If it fails, inspect the
next fatal line after restart.

## Many `/panel/api/status` Lines

Log:

```text
GET /panel/api/status HTTP/1.1" 200
GET /panel/api/sessions?limit=50&offset=0 HTTP/1.1" 200
```

Cause:

Dashboard polling. This is healthy when status is `200`.

Fix:

No fix needed.

## Terminal Or Dashboard 502

Check:

- `ttyd` started and is listening on `7681`.
- `hermes dashboard` started and is listening on `127.0.0.1:9119`.
- `/health` returns `200`.
- `/panel/` returns a page, not JSON `panel_unavailable`.

Common causes:

- Dashboard build failed in upstream image.
- `ttyd` binary missing.
- Ingress proxy path rewrite broke.
- HAOS add-on is still running an older image layer.

Immediate action:

Rebuild add-on in HAOS, not just restart.

## Home Assistant Events Are Dropped

Log:

```text
No watch_domains, watch_entities, or watch_all configured.
```

Cause:

Home Assistant platform is connected, but no event filters are enabled.

Fix:

Set one of:

```yaml
watch_all: true
watch_domains:
  - light
  - sensor
watch_entities:
  - sensor.example
```

## HA WebSocket 502 Loop

Log mentions:

```text
supervisor/core/api/websocket
```

Cause:

Upstream hardcoded `/api/websocket`, but Supervisor proxy needs
`/core/websocket`.

Fix:

Keep `hermes_agent/patches/ha_ws_url.py` active until upstream fixes this
path for Supervisor mode.

## Skill Sync Warnings

Log:

```text
bundled version shipped but you already have a local skill by this name
```

Cause:

User has a local skill copy. Hermes preserves local edits.

Fix:

No fix needed. To replace a local copy with bundled:

```bash
hermes skills reset <skill-name>
```

## Dashboard `Hermes update`

Log:

```text
POST /panel/api/hermes/update HTTP/1.1" 200
```

Risk:

This updates Hermes inside the running container and can drift from the HA
add-on wrapper, Dockerfile, and patches.

Fix:

Use HAOS add-on update/rebuild path instead. If the user already clicked it,
rebuild the add-on from HAOS to restore the image-defined state.
