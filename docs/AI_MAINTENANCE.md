# AI Maintenance Handoff

This file is the first thing future AI maintainers should read after cloning
`sunboss/hermes-agent-ha-addon`.

## Current Target State

- Add-on version: `2026.6.20.0`
- Upstream image: `nousresearch/hermes-agent:v2026.6.19`
- Upstream Hermes release: `v0.17.0`
- HAOS verification: pending
- Prior known-good add-on version: `2026.5.20.0`
- Prior known-good upstream image: `nousresearch/hermes-agent:v2026.5.16`
- Main branch latest required fixes:
  - `a4a2ab2` — render HAOS `/data/options.json` before dropping privileges.
  - `77c91f5` — record HAOS startup verification.
- Repository URL: `https://github.com/sunboss/hermes-agent-ha-addon`

## Maintenance Entry Points

Read these in order:

1. `docs/AI_MAINTENANCE.md` — this handoff.
2. `docs/OPERATIONS_ARCHIVE.md` — operator log, release state, push/rollback flow.
3. `docs/UPGRADE_LOG.md` — root causes behind shipped fixes.
4. `docs/ARCHITECTURE.md` — process layout, storage, routing, pitfalls.
5. `docs/HAOS_RUNBOOK.md` — HAOS update/rebuild/verification commands.
6. `docs/TROUBLESHOOTING.md` — symptom-to-cause lookup.
7. `docs/RELEASE_PROCESS.md` — release, push, Actions, rollback flow.
8. `docs/STORAGE.md` — HAOS storage layout and migration notes.
9. `hermes_agent/CHANGELOG.md` — user-facing release notes.
10. `hermes_agent/run.sh`, `hermes_agent/Dockerfile`, `hermes_agent/scripts/configure.py`.

## Critical Invariants

- Do not call upstream `/opt/hermes/docker/entrypoint.sh`; it owns a generic
  Docker layout and defaults `HERMES_HOME` toward `/opt/data`.
- Do not run `hermes gateway` as root in the official upstream image.
  Upstream v0.14.0 refuses this.
- In `run.sh`, keep the order:
  1. root creates `/config` directories.
  2. root runs `configure.py` while `/data/options.json` is readable.
  3. root `chown -R hermes:hermes /config`.
  4. `gosu hermes`.
  5. `hermes` user starts ttyd, Ingress UI, dashboard, skills sync, gateway.
- Keep Docker `ENTRYPOINT ["/usr/bin/tini", "-g", "--", "/run.sh"]` while
  upstream ships `tini`.
- Keep the upstream image pinned to an explicit calendar tag, not `latest` or
  `main`, unless the user explicitly asks for a risky test build.
- Keep `ha_ws_url.py` until upstream no longer hardcodes `/api/websocket` for
  Home Assistant Supervisor proxy mode.
- Never commit `.ops/secrets.local.md` or `.ops/git-askpass.secret.sh`.

## HAOS Runtime Signals

Healthy logs include:

```text
[run.sh] Dropping root privileges to hermes (HERMES_HOME=/config/.hermes)...
[Hermes UI] Listening on http://0.0.0.0:8099
[run.sh] Starting hermes dashboard on 127.0.0.1:9119...
[run.sh] hermes dashboard started
[run.sh] Starting Hermes Agent gateway (HERMES_HOME=/config/.hermes)...
Hermes Gateway Starting...
```

Healthy request logs include repeated `200` responses for:

```text
/health
/panel/api/status
/panel/api/sessions
/ttyd/
```

`signal=SIGTERM parent_name=tini` after `POST /panel/api/gateway/restart` is
normal. It means the dashboard requested a gateway restart and `tini` is PID 1.

## Known Non-Fatal Warnings

- `spotify` / `design-md` bundled skill conflict warnings mean the user's local
  skill copy was kept. This is expected.
- `No watch_domains, watch_entities, or watch_all configured` means the add-on
  will not react to HA state changes until watch filters are configured.
- `WEIXIN_GROUP_POLICY=open...` is an upstream warning about iLink WeChat group
  delivery. It does not affect Home Assistant startup.

## Avoid This

- Do not use Dashboard `POST /panel/api/hermes/update` as the normal add-on
  update mechanism. HA add-ons should update via repository version bump and
  HAOS rebuild/update so Dockerfile patches and metadata stay consistent.
- Do not set `HERMES_ALLOW_ROOT_GATEWAY=1` as a permanent fix.
- Do not switch `BUILD_FROM` to `main`, `latest`, or a moving `sha-*` tag for a
  stable release.

## Local Verification Commands

```bash
bash -n hermes_agent/run.sh
PYTHONPYCACHEPREFIX="$PWD/.pycache-check" python3 -m py_compile \
  hermes_agent/hermes_ui/server.py \
  hermes_agent/hermes_ui/auth_bridge.py \
  hermes_agent/hermes_ui/provider_shim.py \
  hermes_agent/scripts/_fetch.py \
  hermes_agent/scripts/bake-version.py \
  hermes_agent/scripts/configure.py \
  hermes_agent/patches/ha_ws_url.py
python3 -c "import glob, yaml; [yaml.safe_load(open(f, encoding='utf-8')) for f in glob.glob('hermes_agent/**/*.yaml', recursive=True) + glob.glob('hermes_agent/**/*.yml', recursive=True)]; print('yaml ok')"
git diff --check
```

## Documentation Bundle

The repo includes a generated documentation bundle under:

```text
docs/maintenance_bundle/
```

Regenerate it after documentation changes with:

```bash
./docs/maintenance_bundle/create_bundle.sh
```

The bundle intentionally excludes `.ops/` and all local secrets.

## Current Documentation Map

```text
docs/
├── AI_MAINTENANCE.md      # first-read handoff
├── HAOS_RUNBOOK.md        # HAOS operator commands and healthy signals
├── TROUBLESHOOTING.md     # symptom-to-fix lookup
├── RELEASE_PROCESS.md     # repeatable release checklist
├── OPERATIONS_ARCHIVE.md  # dated operations log
├── UPGRADE_LOG.md         # root-cause fix register
├── ARCHITECTURE.md        # system layout and invariants
├── STORAGE.md             # persistent storage/migration
└── maintenance_bundle/    # portable docs archive
```
