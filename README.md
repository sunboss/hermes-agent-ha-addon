# Hermes Agent Home Assistant Add-on

This repository contains a Home Assistant add-on that builds a custom Hermes Agent image from the upstream [`NousResearch/hermes-agent`](https://github.com/NousResearch/hermes-agent) source tree.

The wrapper does four things:

- pins the upstream Hermes source ref so upgrades stay intentional
- builds Hermes locally during the add-on image build
- injects Home Assistant Supervisor API access into Hermes
- translates add-on options into `~/.hermes/config.yaml` and `~/.hermes/.env`

## Layout

```text
repository.yaml
INSTALL.md
hermes_agent/
  .dockerignore
  build.yaml
  CHANGELOG.md
  config.yaml
  custom_overlay/
  Dockerfile
  DOCS.md
  README.md
  run.sh
  translations/
    en.yaml
```

## Important setup note

This scaffold still contains a placeholder GitHub URL in `repository.yaml` and `hermes_agent/config.yaml`.
Replace that with your real repository URL before adding the repo to Home Assistant.

## Customizing Hermes

Put files under [`hermes_agent/custom_overlay`](./hermes_agent/custom_overlay) to override or add files inside the upstream Hermes checkout during image build.

Examples:

- `custom_overlay/skills/my_skill/SKILL.md`
- `custom_overlay/docker/SOUL.md`
- `custom_overlay/plugins/my_plugin/...`

## Local build

From the add-on directory, a straightforward Docker test build looks like this on `amd64`:

```bash
docker build -t local/hermes-agent-addon .
```

For a Home Assistant-style test build, use the official builder against the add-on folder.

## Upgrade policy

- Do not track upstream `latest` automatically.
- Bump the pinned upstream Hermes ref in [`hermes_agent/Dockerfile`](./hermes_agent/Dockerfile) and [`hermes_agent/build.yaml`](./hermes_agent/build.yaml) on purpose.
- Smoke test startup, Home Assistant API access, and the built-in Home Assistant toolset before publishing a new add-on version.
