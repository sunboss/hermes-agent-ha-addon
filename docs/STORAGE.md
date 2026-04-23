# Storage layout & backup/migration guide

## Container ↔ host path mapping

| 容器内路径 | HA OS 宿主机路径 |
|---|---|
| `/config/` | `/addon_configs/<slug>_hermes_agent/` |
| `/config/.hermes/` | `/addon_configs/<slug>_hermes_agent/.hermes/` |
| `/config/auth/` | `/addon_configs/<slug>_hermes_agent/auth/` |
| `/config/workspace/` | `/addon_configs/<slug>_hermes_agent/workspace/` |
| `/data/options.json` | Supervisor 管理，不在宿主机直接可见 |

`<slug>` 是 HA 为每个 add-on 安装生成的短 hash。在 HA OS SSH 里查询：

```sh
ls /addon_configs/ | grep hermes
```

map 类型为 `addon_config:rw`（HA 2023.11+ 标准），每个 add-on 独立
目录，与主配置 `/homeassistant/` 完全隔离，卸载 add-on 后数据保留。

---

## 目录重要性分级

```
/addon_configs/<slug>_hermes_agent/
├── .hermes/              ★★★ 必保 — Hermes 主状态
│   ├── .env              ★    每次启动重新生成，无需备份
│   ├── config.yaml       ★    每次启动重新生成，无需备份
│   ├── SOUL.md           ★★   自定义后有价值
│   ├── sessions/         ★★★  对话历史（核心数据）
│   ├── memories/         ★★★  代理长期记忆
│   ├── skills/           ★★   自定义 skill（bundled 的会重新同步）
│   ├── hooks/            ★★   自定义 hook
│   ├── cron/             ★★   定时任务
│   └── logs/             ★    可丢弃
├── auth/                 ★★★  必保 — 登录凭证
│   └── session.json      ★★★  OpenAI/provider 授权状态
└── workspace/            ★★   工作目录文件
```

---

## 备份策略

### 方案 A — HA Snapshot（推荐，最简单）

HA Snapshot（Settings → System → Backups → Create）会自动包含
`addon_configs` 下的所有 add-on 数据，包括我们的整个目录。
恢复时选择对应 add-on 数据即可，无需手动操作。

### 方案 B — 手动 tar（SSH，完整备份）

```sh
SLUG=$(ls /addon_configs/ | grep hermes_agent)
tar -czf /homeassistant/hermes-agent-backup-$(date +%Y%m%d).tar.gz \
    -C /addon_configs/${SLUG} .
```

恢复：

```sh
SLUG=$(ls /addon_configs/ | grep hermes_agent)
tar -xzf /homeassistant/hermes-agent-backup-YYYYMMDD.tar.gz \
    -C /addon_configs/${SLUG}
```

### 方案 C — 最小备份（仅关键数据）

```sh
SLUG=$(ls /addon_configs/ | grep hermes_agent)
tar -czf /homeassistant/hermes-minimal-$(date +%Y%m%d).tar.gz \
    -C /addon_configs/${SLUG} \
    .hermes/sessions .hermes/memories .hermes/skills \
    .hermes/hooks .hermes/SOUL.md auth workspace
```

---

## 升级迁移

### v0.11.0+ 正常升级（同一安装实例）

数据在 `addon_config:rw` 挂载下全程保留，直接 Rebuild 即可。
run.sh 包含幂等迁移器，会自动处理老版本布局残留。

### 跨机器迁移 / 重装 HA

1. 在旧机器上执行方案 B 备份
2. 在新机器安装 Hermes Agent add-on（首次启动后立刻 Stop）
3. 查询新机器的 slug：`ls /addon_configs/ | grep hermes`
4. 解压备份到新路径：
   ```sh
   NEW_SLUG=$(ls /addon_configs/ | grep hermes_agent)
   tar -xzf hermes-agent-backup-YYYYMMDD.tar.gz -C /addon_configs/${NEW_SLUG}
   ```
5. Start add-on

### 从 v0.10.x 迁移（旧 homeassistant_config 布局）

旧数据在 `/homeassistant/addons_data/hermes-agent/`，新挂载不会自动看到。
升级到 v0.11.0+ 前，SSH 执行一次：

```sh
SLUG=$(ls /addon_configs/ | grep hermes_agent)
mkdir -p /addon_configs/${SLUG}/
cp -a /homeassistant/addons_data/hermes-agent/. /addon_configs/${SLUG}/
```

然后在 HA 里 Rebuild。确认正常后可选择删除旧目录：

```sh
rm -rf /homeassistant/addons_data/hermes-agent/
```
