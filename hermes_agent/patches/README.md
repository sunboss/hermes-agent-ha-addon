# Upstream patches

Python scripts in this directory are applied at Docker image build time
(`Dockerfile: RUN python3 /opt/hermes-ha-patches/<script>.py`).  Each
patch is **idempotent** (uses a marker comment to skip re-application) and
**non-fatal** (logs a warning and exits 0 if the target pattern is not
found, so that upstream refactors do not break the build).

## ha_ws_url.py

**Symptom fixed:** Gateway reconnection loop every 2–3 seconds:

```
WARNING gateway.platforms.homeassistant: [Homeassistant] Reconnection
failed: 502, url='ws://supervisor/core/api/websocket'
```

**Root cause:** Upstream `hermes.gateway.platforms.homeassistant` hard-codes
`/api/websocket` as the HA WebSocket path.  That suffix is correct for a
direct HA Core endpoint, but the HA Supervisor proxy exposes the WebSocket
at `/core/websocket` — **no `/api` segment**.

**What the patch does:** Replaces the hard-coded line with a conditional:

```python
if 'supervisor' in self._hass_url:
    ws_url = f"{ws_url}/websocket"   # Supervisor proxy (add-on mode)
else:
    ws_url = f"{ws_url}/api/websocket"  # direct HA Core (original)
```

**When this can be removed:** If a future upstream release adds a
`ws_url_path` config option or fixes the Supervisor path detection
natively, this patch becomes unnecessary.  Check with:

```sh
grep -r "api/websocket\|ws_url" /opt/hermes/.venv/lib/python*/site-packages/hermes/gateway/platforms/homeassistant.py
```
