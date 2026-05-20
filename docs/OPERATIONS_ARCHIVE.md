# Operations Archive

This is the maintenance entrypoint for `sunboss/hermes-agent-ha-addon`.
Keep public process notes here, and keep secrets only in the local ignored
file `.ops/secrets.local.md`.

## Current Release State

- Repository: `https://github.com/sunboss/hermes-agent-ha-addon`
- Add-on version: `2026.5.20.0`
- Upstream image: `nousresearch/hermes-agent:v2026.5.16`
- Upstream release: Hermes Agent `v0.14.0`, release date `2026-05-16`
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
git commit -m "Bump Hermes Agent add-on to 2026.5.20.0"
git push origin main
```

Before pushing, confirm `.ops/secrets.local.md` is not staged:

```bash
git status --short --ignored .ops
```

## Rollback Notes

If `v2026.5.16` fails on a Home Assistant host:

1. Revert `BUILD_FROM` in `hermes_agent/Dockerfile` to
   `nousresearch/hermes-agent:v2026.5.7`.
2. Revert add-on version metadata to the last working release.
3. Keep the `gosu hermes` privilege-drop fix unless it is proven to be the
   direct cause. It is compatible with the official image layout and prevents
   root-owned persistent files.
4. Rebuild the add-on from the HA UI.
