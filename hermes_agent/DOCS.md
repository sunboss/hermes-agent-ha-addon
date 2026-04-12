# Hermes Agent

## What this add-on does

This add-on builds Hermes Agent from upstream source and wires it into Home Assistant using the Supervisor proxy.

It writes:

- `/data/.hermes/.env` for secrets and environment variables
- `/data/.hermes/config.yaml` for Hermes runtime settings

Then it starts:

```bash
hermes gateway
```

## Home Assistant access

The add-on uses the Supervisor proxy instead of requiring a manually created long-lived Home Assistant token.

- Home Assistant REST API: `http://supervisor/core/api/`
- Home Assistant WebSocket API: `ws://supervisor/core/websocket`
- Auth token: `SUPERVISOR_TOKEN`

## Custom overlay

If you want to patch Hermes without forking this add-on layout, place overrides under `custom_overlay/`.
During the image build, those files are copied into the upstream Hermes checkout after the pinned ref is checked out.

## Recommended first setup

1. Set `llm_model`
2. Set either `openrouter_api_key` or `openai_base_url` + `openai_api_key`
3. Start with a narrow `watch_domains` list such as `climate`, `binary_sensor`, or `light`
4. Leave `watch_all` disabled unless you really need every state change

## Upgrade workflow

1. Update `HERMES_REF` in `Dockerfile`
2. Bump `version` in `config.yaml`
3. Rebuild and test the add-on
4. Publish only after verifying Hermes can start and call Home Assistant tools successfully

## Known limitations in this scaffold

- No Ingress UI yet
- No automatic upstream image tracking by design
- This first version focuses on Home Assistant events and tools, not a Lovelace chat experience
