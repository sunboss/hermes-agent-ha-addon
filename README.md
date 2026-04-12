# Hermes Agent Home Assistant Add-on

This repository contains a Home Assistant add-on that wraps the official [`nousresearch/hermes-agent`](https://hub.docker.com/r/nousresearch/hermes-agent) image.

The wrapper does three things:

- pins the upstream official Hermes image tag so upgrades stay intentional
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
  Dockerfile
  DOCS.md
  README.md
  run.sh
  translations/
    en.yaml
```

## Local build

From the add-on directory, a straightforward Docker test build looks like this on `amd64`:

```bash
docker build -t local/hermes-agent-addon .
```

For a Home Assistant-style test build, use the official builder against the add-on folder.

## Upgrade policy

- Do not track upstream `latest` automatically.
- Bump the pinned upstream Hermes image tag in [`hermes_agent/Dockerfile`](./hermes_agent/Dockerfile) and [`hermes_agent/build.yaml`](./hermes_agent/build.yaml) on purpose.
- Smoke test startup, Home Assistant API access, and the built-in Home Assistant toolset before publishing a new add-on version.
