const uiText = {
  sidebarCopy: "一个更专注的控制台，用来在 Home Assistant 里调度 Hermes、查看状态和完成对话。",
  labels: {
    gateway: "网关状态",
    conversation: "会话编号",
    model: "当前模型",
    quickPrompts: "快捷提示",
    heroEyebrow: "原生风格控制台",
    heroTitle: "用更沉稳的大屏工作台来操作 Hermes。",
    heroCopy: "界面运行在 Home Assistant 内部，Hermes API 仅保留在本地回环地址，同时提供更适合长期使用的控制体验。",
    sessionFeed: "会话统计",
    heroNote: "可以先点快捷提示，也可以直接输入指令。",
    transcriptLabel: "对话记录",
    transcriptTitle: "实时交互",
    transcriptHintReady: "Hermes 准备就绪后，回复会显示在这里。",
    transcriptHintLive: "新的回复会持续显示在这块对话区域里。",
    emptyKicker: "随时开始",
    emptyTitle: "你可以直接让它查看状态、调用工具或执行动作。",
    emptyCopy: "建议先从系统总览、设备检查，或者让它给出一份 Home Assistant 服务方案开始。",
    inputLabel: "输入消息",
    inputPlaceholder: "比如：帮我检查当前 Home Assistant 状态，看看有没有异常。",
    composerNote: "按 Enter 发送，Shift+Enter 换行。",
    send: "发送给 Hermes",
    reset: "开始新的会话",
    auth: "网页登录桥",
    authTitle: "OpenAI Codex 登录",
    authInputLabel: "回调链接",
    authInputPlaceholder: "把浏览器最终跳转到的完整回调 URL 粘贴到这里，也可以只填 code。",
    authStart: "打开登录页",
    authRefresh: "刷新登录",
    authLogout: "清除会话",
    authExchange: "提交回调",
  },
  prompts: [
    {
      title: "全局巡检",
      prompt: "请总结当前 Home Assistant 的整体情况，并指出任何异常。",
    },
    {
      title: "空调与灯光",
      prompt: "请检查最近的空调和灯光活动，并告诉我最值得关注的变化。",
    },
    {
      title: "自动化建议",
      prompt: "请列出当前适合自动化的 Home Assistant 服务，并给出建议。",
    },
  ],
  statuses: {
    checking: "检查中...",
    pending: "等待中",
    detecting: "识别中...",
    ready: "已就绪",
    unhealthy: "异常",
    unavailable: "不可用",
    authNotRequired: "使用 API Key",
    authNeedsLogin: "等待登录",
    authAwaiting: "等待回调",
    authAuthenticated: "已登录",
    authExpired: "已过期",
    authError: "不可用",
  },
  roles: {
    user: "你",
    assistant: "Hermes",
  },
  messages: {
    apiUnreachable: "Hermes API 暂时无法访问。请先检查模型配置和 add-on 日志。",
    noVisibleText: "Hermes 没有返回可见内容。",
    requestFailed: "请求在 Hermes 作答前失败了。请检查配置或稍后再试。",
    authMissing: "当前处于网页登录模式，请先完成 OpenAI Codex 登录。",
    authStarted: "登录地址已打开。完成浏览器授权后，把回调链接粘贴回来。",
    authCompleted: "网页登录已完成，现在可以继续使用 Hermes。",
    authCleared: "已清除当前网页登录会话。",
    authRefreshed: "网页登录会话已刷新。",
  },
};

const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const sendButton = document.getElementById("send-button");
const errorMessage = document.getElementById("error-message");
const messageTemplate = document.getElementById("message-template");
const healthStatus = document.getElementById("health-status");
const conversationId = document.getElementById("conversation-id");
const modelName = document.getElementById("model-name");
const messageCount = document.getElementById("message-count");
const transcriptHint = document.getElementById("transcript-hint");
const resetButton = document.getElementById("reset-chat");
const promptButtons = Array.from(document.querySelectorAll(".prompt-chip"));
const authTitle = document.getElementById("auth-title");
const authPill = document.getElementById("auth-pill");
const authCopy = document.getElementById("auth-copy");
const authInput = document.getElementById("auth-callback-input");
const authStartButton = document.getElementById("auth-start");
const authRefreshButton = document.getElementById("auth-refresh");
const authLogoutButton = document.getElementById("auth-logout");
const authExchangeButton = document.getElementById("auth-exchange");
const authHelper = document.getElementById("auth-helper");

const conversationStorageKey = "hermes-ingress-conversation";
let currentConversation = localStorage.getItem(conversationStorageKey) || crypto.randomUUID();
let messages = [];
let activeModel = "hermes-agent";
let authStatus = null;

function applyStaticText() {
  document.getElementById("sidebar-copy").textContent = uiText.sidebarCopy;
  document.getElementById("label-gateway").textContent = uiText.labels.gateway;
  document.getElementById("label-conversation").textContent = uiText.labels.conversation;
  document.getElementById("label-model").textContent = uiText.labels.model;
  document.getElementById("quick-prompts-label").textContent = uiText.labels.quickPrompts;
  document.getElementById("hero-eyebrow").textContent = uiText.labels.heroEyebrow;
  document.getElementById("hero-title").textContent = uiText.labels.heroTitle;
  document.getElementById("hero-copy").textContent = uiText.labels.heroCopy;
  document.getElementById("session-feed-label").textContent = uiText.labels.sessionFeed;
  document.getElementById("hero-note").textContent = uiText.labels.heroNote;
  document.getElementById("transcript-label").textContent = uiText.labels.transcriptLabel;
  document.getElementById("transcript-title").textContent = uiText.labels.transcriptTitle;
  document.getElementById("input-label").textContent = uiText.labels.inputLabel;
  document.getElementById("composer-note").textContent = uiText.labels.composerNote;
  document.getElementById("send-button").textContent = uiText.labels.send;
  document.getElementById("reset-chat").textContent = uiText.labels.reset;
  document.getElementById("label-auth").textContent = uiText.labels.auth;
  authTitle.textContent = uiText.labels.authTitle;
  document.getElementById("auth-input-label").textContent = uiText.labels.authInputLabel;
  authInput.placeholder = uiText.labels.authInputPlaceholder;
  authStartButton.textContent = uiText.labels.authStart;
  authRefreshButton.textContent = uiText.labels.authRefresh;
  authLogoutButton.textContent = uiText.labels.authLogout;
  authExchangeButton.textContent = uiText.labels.authExchange;
  chatInput.placeholder = uiText.labels.inputPlaceholder;
  healthStatus.textContent = uiText.statuses.checking;
  conversationId.textContent = uiText.statuses.pending;
  modelName.textContent = uiText.statuses.detecting;
  transcriptHint.textContent = uiText.labels.transcriptHintReady;
  authPill.textContent = uiText.statuses.checking;
  authCopy.textContent = "正在读取认证状态...";
  renderEmptyState();

  promptButtons.forEach((button, index) => {
    const prompt = uiText.prompts[index];
    if (!prompt) {
      return;
    }
    button.textContent = prompt.title;
    button.dataset.prompt = prompt.prompt;
  });
}

function renderEmptyState() {
  const kicker = document.getElementById("empty-kicker");
  const title = document.getElementById("empty-title");
  const copy = document.getElementById("empty-copy");
  if (kicker) kicker.textContent = uiText.labels.emptyKicker;
  if (title) title.textContent = uiText.labels.emptyTitle;
  if (copy) copy.textContent = uiText.labels.emptyCopy;
}

function setError(message = "") {
  if (!message) {
    errorMessage.hidden = true;
    errorMessage.textContent = "";
    return;
  }

  errorMessage.hidden = false;
  errorMessage.textContent = message;
}

function setAuthHelper(message = "") {
  authHelper.textContent = message;
}

function setHealthState(label, state) {
  healthStatus.textContent = label;
  healthStatus.dataset.state = state;
}

function updateMessageCount() {
  const turns = Math.floor(messages.length / 2);
  messageCount.textContent = `${turns} 轮`;
}

function ensureTranscriptIsLive() {
  const emptyState = document.getElementById("empty-state");
  if (emptyState) {
    emptyState.remove();
  }
  transcriptHint.textContent = uiText.labels.transcriptHintLive;
}

function appendMessage(role, content) {
  ensureTranscriptIsLive();

  const fragment = messageTemplate.content.cloneNode(true);
  const article = fragment.querySelector(".message");
  article.dataset.role = role;
  fragment.querySelector(".message-role").textContent = role === "user" ? uiText.roles.user : uiText.roles.assistant;
  fragment.querySelector(".message-body").textContent = content;
  chatLog.appendChild(fragment);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function resetConversation() {
  currentConversation = crypto.randomUUID();
  localStorage.setItem(conversationStorageKey, currentConversation);
  conversationId.textContent = currentConversation.slice(0, 8);
  messages = [];
  chatLog.innerHTML = `
    <div id="empty-state" class="empty-state">
      <p id="empty-kicker" class="empty-kicker"></p>
      <p id="empty-title" class="empty-title"></p>
      <p id="empty-copy" class="empty-copy"></p>
    </div>
  `;
  renderEmptyState();
  setError();
  updateMessageCount();
  transcriptHint.textContent = uiText.labels.transcriptHintReady;
  chatInput.focus();
}

function usePrompt(prompt) {
  chatInput.value = prompt;
  chatInput.focus();
  chatInput.setSelectionRange(prompt.length, prompt.length);
}

function setAuthButtonsDisabled(disabled) {
  authStartButton.disabled = disabled;
  authRefreshButton.disabled = disabled;
  authLogoutButton.disabled = disabled;
  authExchangeButton.disabled = disabled;
}

function applyAuthStatus(status) {
  authStatus = status;
  const state = status?.status || "error";
  const mode = status?.mode || "api_key";
  authPill.dataset.state = state;

  if (mode === "api_key") {
    authPill.textContent = uiText.statuses.authNotRequired;
    authInput.disabled = true;
    authStartButton.disabled = true;
    authRefreshButton.disabled = true;
    authExchangeButton.disabled = true;
    authLogoutButton.disabled = true;
  } else {
    authInput.disabled = false;
    authStartButton.disabled = !status?.oauth_configured;
    authRefreshButton.disabled = !status?.has_session;
    authExchangeButton.disabled = false;
    authLogoutButton.disabled = !status?.has_session && !status?.pending_login;

    if (state === "authenticated") {
      authPill.textContent = uiText.statuses.authAuthenticated;
    } else if (state === "awaiting_callback") {
      authPill.textContent = uiText.statuses.authAwaiting;
    } else if (state === "expired") {
      authPill.textContent = uiText.statuses.authExpired;
    } else if (state === "needs_login") {
      authPill.textContent = uiText.statuses.authNeedsLogin;
    } else {
      authPill.textContent = uiText.statuses.authError;
    }
  }

  authCopy.textContent = status?.message || "认证状态不可用。";

  if (status?.pending_login?.state) {
    setAuthHelper("浏览器登录已发起。完成授权后，把回调链接粘贴到下方并提交。");
  } else if (status?.expires_at) {
    const suffix = status.account_id ? ` 当前账号：${status.account_id}` : "";
    setAuthHelper(`会话有效期至 ${status.expires_at}.${suffix}`);
  } else if (mode === "api_key") {
    setAuthHelper("当前由 API key 驱动，不需要浏览器登录。切换到 web_login 后这里才会启用。");
  } else {
    setAuthHelper("");
  }
}

async function loadModels() {
  try {
    const response = await fetch("./api/v1/models");
    if (!response.ok) {
      modelName.textContent = uiText.statuses.unavailable;
      return;
    }

    const data = await response.json();
    if (Array.isArray(data.data) && data.data.length > 0 && data.data[0].id) {
      activeModel = data.data[0].id;
      modelName.textContent = activeModel;
      return;
    }

    modelName.textContent = activeModel;
  } catch (_) {
    modelName.textContent = activeModel;
  }
}

async function checkHealth() {
  try {
    const response = await fetch("./api/health");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    if (data.status === "ok") {
      setHealthState(uiText.statuses.ready, "ready");
      return;
    }

    setHealthState(uiText.statuses.unhealthy, "error");
  } catch (_) {
    setHealthState(uiText.statuses.unavailable, "error");
    setError(uiText.messages.apiUnreachable);
  }
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  let payload = {};
  try {
    payload = await response.json();
  } catch (_) {
    payload = {};
  }
  if (!response.ok) {
    throw new Error(payload.message || payload.error || `HTTP ${response.status}`);
  }
  return payload;
}

async function loadAuthStatus() {
  try {
    const payload = await fetchJson("./auth/status");
    applyAuthStatus(payload);
  } catch (error) {
    authPill.dataset.state = "error";
    authPill.textContent = uiText.statuses.authError;
    authCopy.textContent = error instanceof Error ? error.message : String(error);
  }
}

async function startAuthFlow() {
  setAuthButtonsDisabled(true);
  setError();
  try {
    const payload = await fetchJson("./auth/start");
    applyAuthStatus(payload.status || authStatus || {});
    if (payload.auth_url) {
      window.open(payload.auth_url, "_blank", "noopener,noreferrer");
    }
    setAuthHelper(payload.message || uiText.messages.authStarted);
  } catch (error) {
    setError(error instanceof Error ? error.message : String(error));
  } finally {
    await loadAuthStatus();
  }
}

async function exchangeAuthCallback() {
  const callbackValue = authInput.value.trim();
  if (!callbackValue) {
    setError("请先粘贴完整回调链接或 code。");
    return;
  }

  setAuthButtonsDisabled(true);
  setError();
  try {
    const payload = await fetchJson("./auth/exchange", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        callback_url: callbackValue.includes("http") ? callbackValue : "",
        code: callbackValue.includes("http") ? undefined : callbackValue,
        state: authStatus?.pending_login?.state,
      }),
    });
    authInput.value = "";
    applyAuthStatus(payload.status || authStatus || {});
    setAuthHelper(payload.message || uiText.messages.authCompleted);
    setError();
  } catch (error) {
    setError(error instanceof Error ? error.message : String(error));
  } finally {
    await loadAuthStatus();
  }
}

async function refreshAuthFlow() {
  setAuthButtonsDisabled(true);
  setError();
  try {
    const payload = await fetchJson("./auth/refresh", { method: "POST" });
    applyAuthStatus(payload.status || authStatus || {});
    setAuthHelper(payload.message || uiText.messages.authRefreshed);
  } catch (error) {
    setError(error instanceof Error ? error.message : String(error));
  } finally {
    await loadAuthStatus();
  }
}

async function logoutAuthFlow() {
  setAuthButtonsDisabled(true);
  setError();
  try {
    const payload = await fetchJson("./auth/logout", { method: "POST" });
    applyAuthStatus(payload);
    setAuthHelper(uiText.messages.authCleared);
  } catch (error) {
    setError(error instanceof Error ? error.message : String(error));
  } finally {
    await loadAuthStatus();
  }
}

async function sendMessage(text) {
  const response = await fetch("./api/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: activeModel,
      messages: [...messages, { role: "user", content: text }],
      stream: false,
    }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed with ${response.status}`);
  }

  return response.json();
}

function extractAssistantText(payload) {
  return payload?.choices?.[0]?.message?.content?.trim() || uiText.messages.noVisibleText;
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = chatInput.value.trim();
  if (!text) {
    return;
  }

  if (authStatus?.mode === "web_login" && !authStatus?.ready) {
    setError(uiText.messages.authMissing);
    return;
  }

  setError();
  sendButton.disabled = true;
  appendMessage("user", text);
  chatInput.value = "";

  try {
    const payload = await sendMessage(text);
    const assistantText = extractAssistantText(payload);
    messages.push({ role: "user", content: text }, { role: "assistant", content: assistantText });
    updateMessageCount();
    appendMessage("assistant", assistantText);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    appendMessage("assistant", uiText.messages.requestFailed);
    setError(message);
  } finally {
    sendButton.disabled = false;
    chatInput.focus();
  }
});

chatInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

promptButtons.forEach((button) => {
  button.addEventListener("click", () => {
    usePrompt(button.dataset.prompt || "");
  });
});

resetButton.addEventListener("click", resetConversation);
authStartButton.addEventListener("click", startAuthFlow);
authExchangeButton.addEventListener("click", exchangeAuthCallback);
authRefreshButton.addEventListener("click", refreshAuthFlow);
authLogoutButton.addEventListener("click", logoutAuthFlow);

async function init() {
  applyStaticText();
  conversationId.textContent = currentConversation.slice(0, 8);
  updateMessageCount();
  await Promise.all([loadModels(), checkHealth(), loadAuthStatus()]);
}

init();

