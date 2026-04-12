# Install Guide

## Before you add the repository

Replace the placeholder repository URL in `repository.yaml` and in the add-on metadata files with your real GitHub repository URL.

Files to update:

- `repository.yaml`
- `hermes_agent/config.yaml`

## Add the repository to Home Assistant

1. Push this repository to GitHub.
2. In Home Assistant, open `Settings -> Add-ons -> Add-on Store`.
3. Open the overflow menu and choose `Repositories`.
4. Add your GitHub repository URL.
5. Open the new `Hermes Agent` add-on entry.

## Recommended first configuration

Use a narrow first-run setup:

- `llm_model`: your chosen model id
- `openrouter_api_key`: if using OpenRouter
- or `openai_base_url` + `openai_api_key`: if using OpenAI-compatible endpoints
- `watch_domains`: start with `climate`, `binary_sensor`, or `light`
- `watch_all`: keep `false`
- `cooldown_seconds`: leave `30`

## First boot validation

After starting the add-on, check the logs for these milestones:

1. The wrapper script starts without shell errors.
2. Hermes writes `/data/.hermes/.env` and `/data/.hermes/config.yaml`.
3. Hermes starts the gateway successfully.
4. Home Assistant events are received for the configured watched domains or entities.

## If startup fails

Check these first:

- Wrong or missing model credentials
- Unsupported model id in `llm_model`
- Pull failure for the upstream official Hermes image
- Too-broad Home Assistant watch settings creating noisy startup behavior

