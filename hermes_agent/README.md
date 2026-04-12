# Hermes Agent Add-on

This folder contains the Home Assistant add-on definition for Hermes Agent.

## Files

- `config.yaml`: add-on metadata, ingress settings, and user options
- `build.yaml`: pinned upstream Hermes image tag
- `Dockerfile`: thin wrapper over the official Hermes image plus the built-in UI assets
- `run.sh`: startup wrapper that writes Hermes config, enables the internal API server, starts the ingress UI server, and launches the gateway
- `hermes_ui/`: the bundled chat-first Web UI and local API proxy

## First run checklist

1. Set `llm_model`
2. Set model credentials such as `openrouter_api_key` or `openai_base_url` + `openai_api_key`
3. Start with focused `watch_domains`
4. Keep `terminal_backend` on `local` for the first run
5. Start the add-on and review logs for successful gateway and Web UI startup
6. Open `OPEN WEB UI` from the add-on page