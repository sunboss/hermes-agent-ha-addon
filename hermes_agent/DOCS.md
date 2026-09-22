# Hermes Agent Add-on Documentation / 插件使用文档

[中文文档 (Chinese)](#中文文档) | [English Documentation](#english-documentation)

---

<a name="中文文档"></a>
# 中文文档

## 一、插件定位与核心架构
本加载项（Add-on）封装了官方 `Hermes Agent` 智能体框架，无缝融入 Home Assistant 生态。采用纯净单核心设计，移除了冗余的外部终端，提供开箱即用的原生交互体验：

1. **HA Ingress 原生直达**：在 Home Assistant 侧边栏点开即直达官方原生 Dashboard 控制面板，无需多余点击。
2. **局域网 9119 原生直连**：对外暴露 `9119` 端口，支持在浏览器中全屏独立访问，无 iframe 嵌套限制。
3. **8642 开放 API 服务**：内置兼容 OpenAI 接口标准的 API 服务（端口 `8642`），支持接入外部客户端（如 Open WebUI、NextChat、LobeChat）。
4. **底层 Supervisor 免密授权**：自动复用 Supervisor Proxy 内部凭据，免去手动生成长效令牌。

---

## 二、快速配置指南 (API Key 模式)
在加载项的「配置 (Configuration)」标签页中配置核心选项：

1. **`openai_base_url`**：API 网关中转地址（例如 `https://api.1234r.com/v1` 或自定义端点）。
2. **`openai_api_key`**：填入您在中转网关或官方平台获取的 API 密钥。
3. **`llm_model`**：具有 Tool-Calling (Function Call) 能力的 Agent 模型名称。
   - **推荐模型**：`gemini-3.8-flash-high`、`deepseek-v3`、`claude-3-5-sonnet`、`gpt-4o`。
   - **注意**：Hermes Agent 是自动化 Agent 框架，必须使用具备工具调用能力的模型；基础非对齐模型将被上游网关拒绝。
4. **`auth_mode`**：保持 `api_key` 模式。
5. **`watch_domains`**：监听并托管控制的 Home Assistant 设备域（例如 `climate`、`light`、`switch` 等）。

---

## 三、网络端口映射与访问方式
在「配置」->「网络 (Network)」卡片中，推荐填入以下端口映射：

| 宿主机端口 | 容器内部端口 | 功能说明与访问入口 |
| :--- | :--- | :--- |
| `9119` | `9119/tcp` | **原生 Web 控制台直连**：浏览器直接打开 `http://<HA_IP>:9119`，全屏极速对话 |
| `8642` | `8642/tcp` | **OpenAI 兼容 API**：供 Open WebUI 等外部客户端调用的 API 端点 |

> **提示**：除了独立端口直连外，您也可以随时在 Home Assistant 左侧边栏点击 **Hermes Agent** 直接在 Ingress 框架内使用。

---

## 四、数据持久化与升级注意事项
- **配置与会话保存路径**：`/config/.hermes/`（对应宿主机 `/addon_configs/<slug>_hermes_agent/`）。
- **版本更新 (Update)**：点击「更新」会**完整保留**您的所有配置、历史对话与 API Key。
- **卸载重装 (Uninstall)**：Home Assistant 会自动销毁专属 Docker 卷。卸载后重新安装需要在配置页重新填入 API Key。

---

<a name="english-documentation"></a>
# English Documentation

## 1. Overview & Core Architecture
This add-on wraps the official `Hermes Agent` framework and integrates it seamlessly into Home Assistant. Designed with a streamlined, single-core philosophy, it eliminates redundant external web terminals to deliver an out-of-the-box native experience:

1. **Direct Ingress Access**: Clicking Hermes Agent in the Home Assistant sidebar immediately loads the official native Dashboard without intermediate landing pages.
2. **Native LAN Direct Access (Port 9119)**: Exposes port `9119` for dedicated, full-screen browser access free from iframe nesting.
3. **OpenAI-Compatible API (Port 8642)**: Built-in OpenAI-compatible API server running on port `8642`, ready to connect external clients (e.g., Open WebUI, NextChat, LobeChat).
4. **Supervisor Auto-Authentication**: Seamlessly utilizes internal Supervisor Proxy tokens without requiring manually generated long-lived access tokens.

---

## 2. Quick Setup Guide (API Key Mode)
Navigate to the **Configuration** tab in the add-on settings:

1. **`openai_base_url`**: API Gateway proxy URL (e.g., `https://api.1234r.com/v1` or your custom endpoint).
2. **`openai_api_key`**: Your API token obtained from your gateway or provider.
3. **`llm_model`**: Agentic model ID capable of Tool-Calling (Function Calling).
   - **Recommended models**: `gemini-3.8-flash-high`, `deepseek-v3`, `claude-3-5-sonnet`, `gpt-4o`.
   - **Notice**: Hermes Agent requires tool-calling models for autonomous operations; basic non-agentic models will be rejected by upstream gateway.
4. **`auth_mode`**: Keep set to `api_key`.
5. **`watch_domains`**: Domains to watch and control within Home Assistant (e.g., `climate`, `light`, `switch`).

---

## 3. Network Ports & Access Methods
Under the **Network** card in the add-on settings, ensure the following host ports are assigned:

| Host Port | Container Port | Purpose & Access Entry |
| :--- | :--- | :--- |
| `9119` | `9119/tcp` | **Native Direct WebUI**: Open `http://<HA_IP>:9119` directly in your browser for full-screen low-latency chat |
| `8642` | `8642/tcp` | **OpenAI-compatible API**: Endpoint for external chat interfaces and tools |

> **Note**: In addition to port 9119 direct access, you can always click **Hermes Agent** in the Home Assistant sidebar to interact directly via Ingress.

---

## 4. Data Persistence & Lifecycle
- **Persistence Path**: Stored in `/config/.hermes/` (maps to `/addon_configs/<slug>_hermes_agent/` on host).
- **Updating the Add-on**: Clicking **Update** preserves all configurations, custom API keys, and conversation history.
- **Uninstalling**: Home Assistant Supervisor wipes the container volume upon uninstallation. If you uninstall and reinstall, you will need to re-enter your API key.
