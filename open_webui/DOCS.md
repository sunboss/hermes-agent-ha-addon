# Home Assistant Add-on: Open WebUI

Open WebUI is an extensible, feature-rich, and user-friendly self-hosted WebUI designed to operate entirely offline while supporting various LLM runners, including Ollama and OpenAI-compatible APIs.

## Features

- **Home Assistant Ingress**: Direct seamless access inside the HA web interface.
- **Persistent Data**: Chats, documents, and configuration saved to `/config/open-webui`.
- **Flexible Backend**: Connect to your local Ollama instance or external OpenAI-compatible gateways.

## Configuration Options

- `openai_api_base_url`: Base URL for OpenAI API (e.g., `http://192.168.1.170:11434/v1` or `https://api.openai.com/v1`).
- `openai_api_key`: Optional API key for the backend service.
- `ollama_base_url`: Base URL for native Ollama API.
- `webui_auth`: Enable/disable user login and password protection (default: `false` for easy home intranet use).
- `webui_name`: Custom header display name.
- `enable_signup`: Allow new user registration when auth is enabled.
