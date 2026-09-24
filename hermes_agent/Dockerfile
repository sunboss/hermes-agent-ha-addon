ARG BUILD_VERSION="2026.9.22.21"
ARG BUILD_FROM="nousresearch/hermes-agent:v2026.9.21"

FROM ${BUILD_FROM}

ARG BUILD_FROM
ARG BUILD_VERSION
ARG BUILD_ARCH

USER root

RUN printf '[Dockerfile] BUILD_FROM=%s  BUILD_ARCH=%s  HOST_ARCH=%s\n' \
      "${BUILD_FROM}" "${BUILD_ARCH}" "$(uname -m)"

ENV HERMES_INSTALL_DIR=/opt/hermes
ENV HERMES_STATE_ROOT=/config
ENV HERMES_HOME=/config/.hermes
ENV HOME=/config
ENV PATH=/opt/hermes/.venv/bin:$PATH
ENV HERMES_PANEL_HOST=127.0.0.1
ENV HERMES_PANEL_PORT=9120

LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.name="Hermes Agent" \
  io.hass.description="Home Assistant app for Hermes Agent — nginx Ingress proxy + direct LAN access." \
  io.hass.url="https://github.com/sunboss/hermes-agent-ha-addon" \
  io.hass.arch="aarch64|amd64"

# 安装 nginx（对齐 Node-RED 架构）
RUN apt-get update && apt-get install -y --no-install-recommends nginx && \
    rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    mkdir -p /etc/profile.d; \
    printf '%s\n' \
      '# Added by hermes-agent-ha-addon' \
      'export HERMES_STATE_ROOT=/config' \
      'export HERMES_HOME=/config/.hermes' \
      'export HOME=/config' \
      'export HERMES_INSTALL_DIR=/opt/hermes' \
      'case ":$PATH:" in' \
      '  *":/opt/hermes/.venv/bin:"*) ;;' \
      '  *) export PATH="/opt/hermes/.venv/bin:$PATH" ;;' \
      'esac' \
      >/etc/profile.d/hermes.sh; \
    chmod 644 /etc/profile.d/hermes.sh

# 拷贝辅助脚本
COPY --chmod=0755 scripts/ /opt/hermes-ha-scripts/

# 拷贝 WebSocket URL 与 PTY Auth / Head Bootstrap 补丁
COPY patches/ /opt/hermes-ha-patches/
RUN /opt/hermes/.venv/bin/python3 /opt/hermes-ha-patches/ha_ws_url.py
RUN /opt/hermes/.venv/bin/python3 /opt/hermes-ha-patches/pty_auth_bypass.py || true
RUN /opt/hermes/.venv/bin/python3 /opt/hermes-ha-patches/head_bootstrap_patch.py || true
RUN /opt/hermes/.venv/bin/python3 /opt/hermes-ha-patches/ingress_chunk_path.py || true

# 拷贝 nginx 配置（对齐 Node-RED 标准反代架构）
COPY rootfs/etc/nginx/nginx.conf /etc/nginx/nginx.conf

# 拷贝启动脚本（不再需要 hermes_ui/server.py 和 native_proxy.py）
COPY run.sh /run.sh
RUN chmod a+x /run.sh

# 烘焙版本号与补丁前端静态资源
COPY hermes_ui/version.json /opt/hermes-ha-ui/version.json
RUN python3 /opt/hermes-ha-scripts/bake-version.py || true
RUN python3 /opt/hermes-ha-scripts/patch-web-dist.py /opt/hermes/hermes_cli/web_dist/index.html || true

ENTRYPOINT ["/run.sh"]
