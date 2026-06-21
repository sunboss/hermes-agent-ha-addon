# HAOS Runbook

Operational steps for installing, updating, rebuilding, and checking the
Hermes Agent Home Assistant add-on on HAOS.

## Repository

Add-on repository URL:

```text
https://github.com/sunboss/hermes-agent-ha-addon
```

Current target add-on version, pending HAOS verification:

```text
2026.6.21.2
```

Current target upstream image:

```text
nousresearch/hermes-agent:v2026.6.19
```

Last known-good add-on version: `2026.5.20.0`

Last known-good upstream image: `nousresearch/hermes-agent:v2026.5.16`

## Install Or Refresh Repository

In Home Assistant:

1. `Settings -> Add-ons -> Add-on Store`.
2. Top-right menu.
3. `Repositories`.
4. Add or verify:
   `https://github.com/sunboss/hermes-agent-ha-addon`.
5. Close and use `Check for updates` / `Reload`.

From HAOS Terminal/SSH:

```bash
ha store reload
ha supervisor reload
```

If updates still do not appear, inspect the installed slug:

```bash
ha addons list | grep -i hermes
ha addons info <slug>
```

Look for the installed version and latest version fields.

## Update / Rebuild

Preferred path:

1. Pull the latest repository metadata in HAOS (`ha store reload`).
2. Use the Home Assistant add-on UI `Update` if offered.
3. If no update is offered but the repository is known to be newer, use
   `Rebuild` from the add-on page.
4. Start the add-on and watch logs.

Command-line fallback:

```bash
ha addons rebuild <slug>
ha addons start <slug>
ha addons logs <slug>
```

## Healthy Startup Signals

Good startup contains these lines in this order:

```text
[run.sh] Dropping root privileges to hermes (HERMES_HOME=/config/.hermes)...
[Hermes UI] Listening on http://0.0.0.0:8099
[run.sh] Starting hermes dashboard on 127.0.0.1:9119...
[run.sh] hermes dashboard started
[run.sh] Starting Hermes Agent gateway (HERMES_HOME=/config/.hermes)...
Hermes Gateway Starting...
```

Healthy HTTP polling looks like:

```text
GET /health HTTP/1.1" 200
GET /panel/api/status HTTP/1.1" 200
GET /panel/api/sessions?limit=50&offset=0 HTTP/1.1" 200
HEAD /panel/ HTTP/1.1" 200
HEAD /ttyd/ HTTP/1.1" 200
```

## Runtime Warnings

These are expected unless the user wants those specific features:

- `No watch_domains, watch_entities, or watch_all configured`:
  Hermes will not react to HA state changes. Configure watch filters or
  set `watch_all: true`.
- `spotify` / `design-md` local skill warnings:
  Local user skill copies were preserved.
- `WEIXIN_GROUP_POLICY=open...`:
  Upstream warning about iLink WeChat group delivery; not an add-on boot issue.

## Avoid Dashboard Self-Update

The upstream dashboard exposes:

```text
POST /panel/api/hermes/update
```

Do not use this as the normal HA add-on update mechanism. It can update code
inside the container without updating this repository's Dockerfile, patches,
metadata, or HA wrapper scripts. Use HAOS update/rebuild from this add-on
repository instead.

## Collect Evidence

When reporting a problem, collect:

```bash
ha addons info <slug>
ha addons logs <slug>
ha supervisor logs | grep -i "hermes\|github\|repository\|store\|addon\|build"
```

Also capture:

- Add-on version shown in HA UI.
- Whether the user clicked Dashboard `Hermes update`.
- Whether this was `Update`, `Rebuild`, or fresh install.
- First fatal line before Supervisor restarts the add-on.

## Rollback

If a release fails and HAOS cannot run the add-on:

1. Revert this repository to the previous known-good version.
2. Push `main`.
3. In HAOS, reload store metadata.
4. Rebuild the add-on.
5. Keep persistent `/config` data unless the failure is explicitly data-related.

Do not delete `/addon_configs/<slug>_hermes_agent/` unless the user accepts
losing Hermes state, sessions, auth, skills, and workspace data.
