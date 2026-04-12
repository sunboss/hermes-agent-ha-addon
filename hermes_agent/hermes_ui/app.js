const uiText = {
  sidebarCopy: "\u4e00\u4e2a\u66f4\u4e13\u6ce8\u7684\u63a7\u5236\u53f0\uff0c\u7528\u6765\u5728 Home Assistant \u91cc\u8c03\u5ea6 Hermes\u3001\u67e5\u770b\u72b6\u6001\u548c\u5b8c\u6210\u5bf9\u8bdd\u3002",
  labels: {
    gateway: "\u7f51\u5173\u72b6\u6001",
    conversation: "\u4f1a\u8bdd\u7f16\u53f7",
    model: "\u5f53\u524d\u6a21\u578b",
    quickPrompts: "\u5feb\u6377\u63d0\u793a",
    heroEyebrow: "\u539f\u751f\u98ce\u683c\u63a7\u5236\u53f0",
    heroTitle: "\u7528\u66f4\u6c89\u7a33\u7684\u5927\u5c4f\u5de5\u4f5c\u53f0\u6765\u64cd\u4f5c Hermes\u3002",
    heroCopy: "\u754c\u9762\u8fd0\u884c\u5728 Home Assistant \u5185\u90e8\uff0cHermes API \u4ec5\u4fdd\u7559\u5728\u672c\u5730\u56de\u73af\u5730\u5740\uff0c\u540c\u65f6\u63d0\u4f9b\u66f4\u9002\u5408\u957f\u671f\u4f7f\u7528\u7684\u63a7\u5236\u4f53\u9a8c\u3002",
    sessionFeed: "\u4f1a\u8bdd\u7edf\u8ba1",
    heroNote: "\u53ef\u4ee5\u5148\u70b9\u5feb\u6377\u63d0\u793a\uff0c\u4e5f\u53ef\u4ee5\u76f4\u63a5\u8f93\u5165\u6307\u4ee4\u3002",
    transcriptLabel: "\u5bf9\u8bdd\u8bb0\u5f55",
    transcriptTitle: "\u5b9e\u65f6\u4ea4\u4e92",
    transcriptHintReady: "Hermes \u51c6\u5907\u5c31\u7eea\u540e\uff0c\u56de\u590d\u4f1a\u663e\u793a\u5728\u8fd9\u91cc\u3002",
    transcriptHintLive: "\u65b0\u7684\u56de\u590d\u4f1a\u6301\u7eed\u663e\u793a\u5728\u8fd9\u5757\u5bf9\u8bdd\u533a\u57df\u91cc\u3002",
    emptyKicker: "\u968f\u65f6\u5f00\u59cb",
    emptyTitle: "\u4f60\u53ef\u4ee5\u76f4\u63a5\u8ba9\u5b83\u67e5\u770b\u72b6\u6001\u3001\u8c03\u7528\u5de5\u5177\u6216\u6267\u884c\u52a8\u4f5c\u3002",
    emptyCopy: "\u5efa\u8bae\u5148\u4ece\u7cfb\u7edf\u603b\u89c8\u3001\u8bbe\u5907\u68c0\u67e5\uff0c\u6216\u8005\u8ba9\u5b83\u7ed9\u51fa\u4e00\u4efd Home Assistant \u670d\u52a1\u65b9\u6848\u5f00\u59cb\u3002",
    inputLabel: "\u8f93\u5165\u6d88\u606f",
    inputPlaceholder: "\u6bd4\u5982\uff1a\u5e2e\u6211\u68c0\u67e5\u5f53\u524d Home Assistant \u72b6\u6001\uff0c\u770b\u770b\u6709\u6ca1\u6709\u5f02\u5e38\u3002",
    composerNote: "\u6309 Enter \u53d1\u9001\uff0cShift+Enter \u6362\u884c\u3002",
    send: "\u53d1\u9001\u7ed9 Hermes",
    reset: "\u5f00\u59cb\u65b0\u7684\u4f1a\u8bdd",
  },
  prompts: [
    {
      title: "\u5168\u5c40\u5de1\u68c0",
      prompt: "\u8bf7\u603b\u7ed3\u5f53\u524d Home Assistant \u7684\u6574\u4f53\u60c5\u51b5\uff0c\u5e76\u6307\u51fa\u4efb\u4f55\u5f02\u5e38\u3002",
    },
    {
      title: "\u7a7a\u8c03\u4e0e\u706f\u5149",
      prompt: "\u8bf7\u68c0\u67e5\u6700\u8fd1\u7684\u7a7a\u8c03\u548c\u706f\u5149\u6d3b\u52a8\uff0c\u5e76\u544a\u8bc9\u6211\u6700\u503c\u5f97\u5173\u6ce8\u7684\u53d8\u5316\u3002",
    },
    {
      title: "\u81ea\u52a8\u5316\u5efa\u8bae",
      prompt: "\u8bf7\u5217\u51fa\u5f53\u524d\u9002\u5408\u81ea\u52a8\u5316\u7684 Home Assistant \u670d\u52a1\uff0c\u5e76\u7ed9\u51fa\u5efa\u8bae\u3002",
    },
  ],
  statuses: {
    checking: "\u68c0\u67e5\u4e2d...",
    pending: "\u7b49\u5f85\u4e2d",
    detecting: "\u8bc6\u522b\u4e2d...",
    ready: "\u5df2\u5c31\u7eea",
    unhealthy: "\u5f02\u5e38",
    unavailable: "\u4e0d\u53ef\u7528",
  },
  roles: {
    user: "\u4f60",
    assistant: "Hermes",
  },
  messages: {
    apiUnreachable: "Hermes API \u6682\u65f6\u65e0\u6cd5\u8bbf\u95ee\u3002\u8bf7\u5148\u68c0\u67e5\u6a21\u578b\u914d\u7f6e\u548c add-on \u65e5\u5fd7\u3002",
    noVisibleText: "Hermes \u6ca1\u6709\u8fd4\u56de\u53ef\u89c1\u5185\u5bb9\u3002",
    requestFailed: "\u8bf7\u6c42\u5728 Hermes \u4f5c\u7b54\u524d\u5931\u8d25\u4e86\u3002\u8bf7\u68c0\u67e5\u914d\u7f6e\u6216\u7a0d\u540e\u518d\u8bd5\u3002",
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

const conversationStorageKey = "hermes-ingress-conversation";
let currentConversation = localStorage.getItem(conversationStorageKey) || crypto.randomUUID();
let messages = [];
let activeModel = "hermes-agent";

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
  chatInput.placeholder = uiText.labels.inputPlaceholder;
  healthStatus.textContent = uiText.statuses.checking;
  conversationId.textContent = uiText.statuses.pending;
  modelName.textContent = uiText.statuses.detecting;
  transcriptHint.textContent = uiText.labels.transcriptHintReady;
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

function setHealthState(label, state) {
  healthStatus.textContent = label;
  healthStatus.dataset.state = state;
}

function updateMessageCount() {
  const turns = Math.floor(messages.length / 2);
  messageCount.textContent = `${turns} \u8f6e`;
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

async function init() {
  applyStaticText();
  conversationId.textContent = currentConversation.slice(0, 8);
  updateMessageCount();
  await loadModels();
  await checkHealth();
}

init();