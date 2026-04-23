window.onerror = function (msg, src, line, col, err) {
  const banner = document.getElementById("js-error-banner");
  if (banner) {
    banner.textContent =
      "Hermes UI 运行出错：" +
      (err && err.message ? err.message : msg) +
      "。请强制刷新页面，或稍后重新打开。";
    banner.hidden = false;
  }
  return false;
};

window.onunhandledrejection = function (event) {
  console.error("[Hermes UI] unhandled promise rejection:", event.reason);
};

const textMap = {
  status: {
    checking: "检查中",
    detecting: "识别中",
    ready: "已就绪",
    starting: "启动中",
    unhealthy: "异常",
    unavailable: "不可用",
  },
  detail: {
    gatewayReady: "Hermes 网关已连接，Dashboard 与终端入口都可直接使用。",
    gatewayStarting: "UI 已启动，但 Hermes 网关仍在初始化中，请稍候几秒。",
    gatewayUnhealthy: "网关返回了异常状态，请检查 add-on 日志。",
    gatewayUnavailable: "暂时无法连接 Hermes 网关，请检查启动日志。",
  },
};

// ── Element refs ──────────────────────────────────────────────────────────────
const modelNameEl    = document.getElementById("model-name");
const modelProviderEl = document.getElementById("model-provider");
const healthStatusEl = document.getElementById("health-status");
const healthDetailEl = document.getElementById("health-detail");
const dotPanelEl     = document.getElementById("dot-panel");
const dotTtydEl      = document.getElementById("dot-ttyd");
const launchPanelEl  = document.getElementById("launch-panel");
const launchTermEl   = document.getElementById("launch-terminal");

// ── Helpers ───────────────────────────────────────────────────────────────────
function setText(el, value) {
  if (el) el.textContent = value;
}

function removeSkeleton(el) {
  if (el) el.classList.remove("is-loading");
}

function setHealth(state, label, detail) {
  if (healthStatusEl) {
    healthStatusEl.dataset.state = state;
    healthStatusEl.textContent = label;
    removeSkeleton(healthStatusEl);
  }
  setText(healthDetailEl, detail);
}

function setServiceDot(dotEl, cardEl, state) {
  if (dotEl) {
    dotEl.dataset.state = state;
    dotEl.title =
      state === "ok"          ? "服务运行正常" :
      state === "unavailable" ? "服务暂不可用" :
                                "检查服务可用性…";
  }
  if (cardEl) {
    cardEl.dataset.status = state === "checking" ? "checking" : state;
    // Only disable pointer-events when confirmed unavailable (not merely checking).
    // CSS handles .launch-card[data-status="unavailable"] opacity + pointer-events.
  }
}

// ── Model detection ───────────────────────────────────────────────────────────
async function loadConfiguredModel() {
  try {
    const res = await fetch("./config-model", { cache: "no-store" });
    if (!res.ok) throw new Error("config-model " + res.status);
    const data = await res.json();
    const model    = data && data.model    ? String(data.model)    : "";
    const provider = data && data.provider ? String(data.provider) : "";
    if (model) {
      setText(modelNameEl, model);
      setText(modelProviderEl, provider);
      removeSkeleton(modelNameEl);
      return;
    }
  } catch (_) {}

  try {
    const res = await fetch("./models", { cache: "no-store" });
    if (!res.ok) throw new Error("models " + res.status);
    const data  = await res.json();
    const first = Array.isArray(data.data) ? data.data[0] : null;
    if (first && first.id) {
      setText(modelNameEl, String(first.id));
      setText(modelProviderEl, "");
      removeSkeleton(modelNameEl);
      return;
    }
  } catch (_) {}

  setText(modelNameEl, textMap.status.unavailable);
  setText(modelProviderEl, "");
  removeSkeleton(modelNameEl);
}

// ── Gateway health ─────────────────────────────────────────────────────────────
let _healthInterval = null;

async function checkHealth() {
  try {
    const res = await fetch("./health", { cache: "no-store" });
    if (!res.ok) throw new Error("health " + res.status);
    const data = await res.json();
    if (data.status === "ok" && data.gateway === "ready") {
      setHealth("ready", textMap.status.ready, textMap.detail.gatewayReady);
      _scheduleHealthPoll(30_000);
      return;
    }
    if (data.status === "ok") {
      setHealth("starting", textMap.status.starting, textMap.detail.gatewayStarting);
      // Gateway still initialising — retry quickly, then slow down.
      setTimeout(checkHealth, 5000);
      return;
    }
    setHealth("error", textMap.status.unhealthy, textMap.detail.gatewayUnhealthy);
    _scheduleHealthPoll(30_000);
  } catch (_) {
    setHealth("error", textMap.status.unavailable, textMap.detail.gatewayUnavailable);
    _scheduleHealthPoll(30_000);
  }
}

function _scheduleHealthPoll(ms) {
  if (_healthInterval) return; // already scheduled
  _healthInterval = setInterval(checkHealth, ms);
}

// ── Service availability pre-check ────────────────────────────────────────────
async function checkService(url, dotEl, cardEl) {
  try {
    // HEAD is enough — just need a non-5xx response.
    const res = await fetch(url, { method: "HEAD", cache: "no-store" });
    const ok = res.ok || res.status === 301 || res.status === 302 || res.status === 200;
    setServiceDot(dotEl, cardEl, ok ? "ok" : "unavailable");
  } catch (_) {
    // Network error / 5xx: mark unavailable.
    setServiceDot(dotEl, cardEl, "unavailable");
  }
}

async function checkServices() {
  // Run both checks concurrently. We don't block each other.
  await Promise.all([
    checkService("./panel/", dotPanelEl, launchPanelEl),
    checkService("./ttyd/",  dotTtydEl,  launchTermEl),
  ]);
  // Re-check every 30 seconds so the UI stays in sync if a service recovers.
  setTimeout(checkServices, 30_000);
}

// ── Boot ──────────────────────────────────────────────────────────────────────
function init() {
  setText(modelNameEl, textMap.status.detecting);
  setText(modelProviderEl, "");
  setHealth("checking", textMap.status.checking, "正在连接 Hermes 网关");
  // model-name starts with is-loading in HTML; health-status too.
  // checkHealth / loadConfiguredModel will call removeSkeleton when done.

  void Promise.all([loadConfiguredModel(), checkHealth(), checkServices()]);
}

init();
