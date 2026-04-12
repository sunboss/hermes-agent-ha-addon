# Hermes Agent

## What this add-on does

This add-on wraps the official Hermes Agent image and wires it into Home Assistant using the Supervisor proxy while staying close to the native Hermes Docker startup flow.

It updates:

- `/data/.env` for secrets and environment variables
- `/data/config.yaml` for Hermes runtime settings

Then it hands off to the official Hermes Docker entrypoint and starts `hermes gateway`.

## Home Assistant access

The add-on uses the Supervisor proxy instead of requiring a manually created long-lived Home Assistant token.

- Home Assistant REST API: `http://supervisor/core/api/`
- Home Assistant WebSocket API: `ws://supervisor/core/websocket`
- Auth token: `SUPERVISOR_TOKEN`

## Recommended first setup

1. Set `llm_model`
2. Set either `openrouter_api_key` or `openai_base_url` + `openai_api_key`
3. Start with a narrow `watch_domains` list such as `climate`, `binary_sensor`, or `light`
4. Leave `watch_all` disabled unless you really need every state change

## Upgrade workflow

1. Update `HERMES_IMAGE_TAG` in `Dockerfile`
2. Bump `version` in `config.yaml`
3. Rebuild and test the add-on
4. Publish only after verifying Hermes can start and call Home Assistant tools successfully

## Known limitations in this scaffold

- No Ingress UI yet
- No automatic upstream image tracking by design
- This first version focuses on Home Assistant events and tools, not a Lovelace chat experience
