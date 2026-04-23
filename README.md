# Hermes Agent Home Assistant Add-on Repository

![Hermes Agent Home Assistant Add-on](./hermes_agent/logo.png)

[![Open your Home Assistant instance and show the add add-on repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fsunboss%2Fhermes-agent-ha-addon)
[![GitHub last commit](https://img.shields.io/github/last-commit/sunboss/hermes-agent-ha-addon)](https://github.com/sunboss/hermes-agent-ha-addon/commits/main)
[![GitHub license](https://img.shields.io/github/license/sunboss/hermes-agent-ha-addon)](./LICENSE)
![Supports aarch64](https://img.shields.io/badge/aarch64-yes-green.svg)
![Supports amd64](https://img.shields.io/badge/amd64-yes-green.svg)
![Home Assistant Add-on](https://img.shields.io/badge/Home%20Assistant-Add--on-18bcf2?logo=homeassistant&logoColor=white)

这个仓库提供一个 Home Assistant add-on，用来运行官方 `Hermes Agent`，并补上：

- Home Assistant Ingress 入口
- 官方 `hermes dashboard` 代理
- `ttyd` 原生命令行
- Supervisor Core API 默认接入
- 面向 Home Assistant 的持久化目录布局

当前版本：

- add-on: `0.10.1`
- upstream Hermes: `v2026.4.16`

## 安装

1. 打开 `Settings -> Add-ons -> Add-on Store`
2. 打开右上角菜单 `Repositories`
3. 添加仓库：`https://github.com/sunboss/hermes-agent-ha-addon`
4. 安装 **Hermes Agent**
5. 启动后点击 **OPEN WEB UI**

## 这版重点

- 升级到 Hermes 官方最新镜像 `v2026.4.16`
- `Dockerfile` 与 `build.yaml` 改成 digest 固定
- 规范化存储布局到 HA 2023.11+ 标准 `addon_config:rw`：宿主机 `/addon_configs/<slug>_hermes_agent/`，每个 add-on 独立隔离目录，不再污染主 `/homeassistant/` 配置
- 扁平化容器内路径：`/config/.hermes`、`/config/workspace`、`/config/auth`（不再嵌套 `addons_data/hermes-agent/`）
- Ingress 首页保留两个原生入口：`Hermes Dashboard` 与 `Hermes Terminal`
- 版本号 `0.11.0`

## 数据目录

容器内：

```text
/config/             ← 通过 addon_config:rw 挂载到宿主机 /addon_configs/<slug>_hermes_agent/
├── .hermes/         ← Hermes 主数据（.env、config.yaml、sessions、skills 等）
├── workspace/       ← ttyd 终端工作目录、messaging 数据
└── auth/            ← add-on 认证桥状态（session.json 等）
```

宿主机路径（HA OS SSH 下查看）：`/addon_configs/<slug>_hermes_agent/`（`<slug>` 通过 `ls /addon_configs/` 查实际 hash）

`/data/options.json` 仍由 Supervisor 管理，用作 add-on 配置输入。

## 文档

- 安装说明：[INSTALL.md](./INSTALL.md)
- add-on 文档：[hermes_agent/DOCS.md](./hermes_agent/DOCS.md)
- 架构说明：[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
- 官方 Hermes 文档：[hermes-agent.nousresearch.com/docs](https://hermes-agent.nousresearch.com/docs/)
