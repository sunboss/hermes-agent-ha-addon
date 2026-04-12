# Hermes Agent Add-on

This folder contains the Home Assistant add-on definition for Hermes Agent.

## Files

- `config.yaml`: add-on metadata, ingress settings, and user options
- `build.yaml`: pinned upstream Hermes image tag
- `Dockerfile`: thin wrapper over the official Hermes image plus the built-in UI assets
- `run.sh`: startup wrapper that writes Hermes config, bootstraps auth bridge state, enables the internal API server, starts the ingress UI server, and launches the gateway
- `hermes_ui/`: the bundled chat-first Web UI, auth bridge helpers, and local API proxy

## First run checklist

1. Set `llm_model`
2. Set `auth_mode`
3. If `auth_mode=api_key`, set model credentials such as `openrouter_api_key` or `openai_base_url` + `openai_api_key`
4. If `auth_mode=web_login`, set the OpenAI OAuth fields you need for the PKCE bridge
5. Keep `terminal_backend` on `local` for the first run
6. Start with focused `watch_domains`
7. Start the add-on and review logs for successful gateway and Web UI startup
8. Open `OPEN WEB UI` from the add-on page
9. If testing `web_login`, validate `/auth/status`, `/auth/start`, `/auth/exchange`, and `/auth/refresh`

## Current browser-login scope

The browser-login bridge now handles session setup and lifecycle for `openai_web`, but it is not yet the active model execution path for Hermes chat completions.
Use `auth_mode=api_key` for actual chatting today, and `auth_mode=web_login` when you want to validate the browser session flow.

