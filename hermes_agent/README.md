# Hermes Agent Add-on

This folder contains the Home Assistant add-on definition for Hermes Agent.

## Files

- `config.yaml`: add-on metadata and user options
- `build.yaml`: pinned upstream Hermes image tag
- `Dockerfile`: thin wrapper over the official Hermes image
- `run.sh`: startup wrapper that writes Hermes config and launches the gateway

## First run checklist

1. Set `llm_model`
2. Set model credentials such as `openrouter_api_key` or `openai_base_url` + `openai_api_key`
3. Start with focused `watch_domains`
4. Install the add-on and review logs for successful Home Assistant gateway startup
