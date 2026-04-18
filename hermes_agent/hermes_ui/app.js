window.onerror = function (msg, src, line, col, err) {
  const banner = document.getElementById("js-error-banner");
  if (banner) {
    banner.textContent =
      "Hermes UI \u8fd0\u884c\u51fa\u9519\uff1a" +
      (err && err.message ? err.message : msg) +
      "\u3002\u8bf7\u5f3a\u5236\u5237\u65b0\u9875\u9762\uff0c\u6216\u7a0d\u540e\u91cd\u65b0\u6253\u5f00\u3002";
    banner.hidden = false;
  }
  return false;
};

window.onunhandledrejection = function (event) {
  console.error("[Hermes UI] unhandled promise rejection:", event.reason);
};

const textMap = {
  status: {
    checking: "\u68c0\u67e5\u4e2d",
    detecting: "\u8bc6\u522b\u4e2d",
    ready: "\u5df2\u5c31\u7eea",
    starting: "\u542f\u52a8\u4e2d",
    unhealthy: "\u5f02\u5e38",
    unavailable: "\u4e0d\u53ef\u7528",
  },
  detail: {
    gatewayReady: "Hermes \u7f51\u5173\u5df2\u8fde\u63a5\uff0cDashboard \u4e0e\u7ec8\u7aef\u5165\u53e3\u90fd\u53ef\u76f4\u63a5\u4f7f\u7528\u3002",
    gatewayStarting: "UI \u5df2\u542f\u52a8\uff0c\u4f46 Hermes \u7f51\u5173\u4ecd\u5728\u521d\u59cb\u5316\u4e2d\uff0c\u8bf7\u7a0d\u5019\u51e0\u79d2\u3002",
    gatewayUnhealthy: "\u7f51\u5173\u8fd4\u56de\u4e86\u5f02\u5e38\u72b6\u6001\uff0c\u8bf7\u68c0\u67e5 add-on \u65e5\u5fd7\u3002",
    gatewayUnavailable: "\u6682\u65f6\u65e0\u6cd5\u8fde\u63a5 Hermes \u7f51\u5173\uff0c\u8bf7\u68c0\u67e5\u542f\u52a8\u65e5\u5fd7\u3002",
  },
};

const modelNameEl = document.getElementById("model-name");
const modelProviderEl = document.getElementById("model-provider");
const healthStatusEl = document.getElementById("health-status");
const healthDetailEl = document.getElementById("health-detail");

function setText(element, value) {
  if (element) {
    element.textContent = value;
  }
}

function setHealth(state, label, detail) {
  if (healthStatusEl) {
    healthStatusEl.dataset.state = state;
    healthStatusEl.textContent = label;
  }
  setText(healthDetailEl, detail);
}

async function loadConfiguredModel() {
  try {
    const response = await fetch("./config-model", { cache: "no-store" });
    if (!response.ok) {
      throw new Error("config-model " + response.status);
    }
    const data = await response.json();
    const model = data && data.model ? String(data.model) : "";
    const provider = data && data.provider ? String(data.provider) : "";
    if (model) {
      setText(modelNameEl, model);
      setText(modelProviderEl, provider);
      return;
    }
  } catch (_) {}

  try {
    const response = await fetch("./models", { cache: "no-store" });
    if (!response.ok) {
      throw new Error("models " + response.status);
    }
    const data = await response.json();
    const first = Array.isArray(data.data) ? data.data[0] : null;
    if (first && first.id) {
      setText(modelNameEl, String(first.id));
      setText(modelProviderEl, "");
      return;
    }
  } catch (_) {}

  setText(modelNameEl, textMap.status.unavailable);
  setText(modelProviderEl, "");
}

async function checkHealth() {
  try {
    const response = await fetch("./health", { cache: "no-store" });
    if (!response.ok) {
      throw new Error("health " + response.status);
    }
    const data = await response.json();
    if (data.status === "ok" && data.gateway === "ready") {
      setHealth("ready", textMap.status.ready, textMap.detail.gatewayReady);
      return;
    }
    if (data.status === "ok") {
      setHealth("starting", textMap.status.starting, textMap.detail.gatewayStarting);
      setTimeout(checkHealth, 5000);
      return;
    }
    setHealth("error", textMap.status.unhealthy, textMap.detail.gatewayUnhealthy);
  } catch (_) {
    setHealth("error", textMap.status.unavailable, textMap.detail.gatewayUnavailable);
  }
}

function init() {
  setText(modelNameEl, textMap.status.detecting);
  setText(modelProviderEl, "");
  setHealth("checking", textMap.status.checking, "\u6b63\u5728\u8fde\u63a5 Hermes \u7f51\u5173");
  void Promise.all([loadConfiguredModel(), checkHealth()]);
}

init();
