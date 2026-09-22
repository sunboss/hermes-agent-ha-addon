# Hermes Agent Home Assistant Add-on / 插件目录说明

[中文说明](#中文说明) | [English Overview](#english-overview)

---

## 中文说明

本目录包含适用于 Home Assistant 的 Hermes Agent 加载项定义。

### 目录与文件清单
- **`config.yaml`**：插件元数据、选项配置架构（Schema）、端口映射（`9119/tcp` 与 `8642/tcp`）及 Ingress 声明。
- **`Dockerfile`**：构建精简容器镜像，设置 root 初始化与非 root 运行时安全降权，注入自适应补丁。
- **`run.sh`**：容器启动主编排脚本，负责配置参数解析、权限切换、Dashboard 与 Native Proxy 启动及网关执行。
- **`hermes_ui/`**：
  - `server.py`：Ingress 代理服务，实现请求转发、透明 WebSocket 握手伪装（重写 Origin 杜绝 403 阻断）及根路径直达官方 Dashboard。
  - `native_proxy.py`：局域网 `9119` 直连轻量代理，实现 `0.0.0.0` 安全绑定与全屏对话加速。
- **`scripts/`**：构建时与运行时辅助工具（配置转换、版本注入）。
- **`patches/`**：针对 Home Assistant Supervisor WebSocket 代理的动态兼容补丁。

---

## English Overview

This folder contains the Home Assistant add-on implementation for Hermes Agent.

### Files and Directory Layout
- **`config.yaml`**: Add-on metadata, schema options, port declarations (`9119/tcp` and `8642/tcp`), and Ingress specification.
- **`Dockerfile`**: Lightweight container build instructions with privilege dropping and automated runtime patching.
- **`run.sh`**: Primary entrypoint orchestrating configuration rendering, privilege management, proxy initialization, and gateway launch.
- **`hermes_ui/`**:
  - `server.py`: Ingress proxy providing route translation, transparent WebSocket Origin spoofing (preventing 403 Forbidden handshakes), and direct Dashboard navigation.
  - `native_proxy.py`: LAN port `9119` direct lightweight proxy providing safe non-loopback binding and low-latency chat streaming.
- **`scripts/`**: Build-time and runtime automation utilities.
- **`patches/`**: Compatibility patches for Home Assistant Supervisor WebSocket routing.
