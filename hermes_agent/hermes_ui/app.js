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

conversationId.textContent = currentConversation.slice(0, 8);
updateMessageCount();

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
  messageCount.textContent = `${turns} ${turns === 1 ? "turn" : "turns"}`;
}

function ensureTranscriptIsLive() {
  const emptyState = document.getElementById("empty-state");
  if (emptyState) {
    emptyState.remove();
  }
  transcriptHint.textContent = "Conversation updates stream into this surface as each reply lands.";
}

function appendMessage(role, content) {
  ensureTranscriptIsLive();

  const fragment = messageTemplate.content.cloneNode(true);
  const article = fragment.querySelector(".message");
  article.dataset.role = role;
  fragment.querySelector(".message-role").textContent = role;
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
      <p class="empty-kicker">Ready when you are</p>
      <p class="empty-title">Ask for state, tools, or action.</p>
      <p class="empty-copy">Try a system overview, a device check, or a Home Assistant service plan to start the session with something concrete.</p>
    </div>
  `;
  setError();
  updateMessageCount();
  transcriptHint.textContent = "Hermes answers appear here as soon as the gateway is ready.";
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
      modelName.textContent = "Unavailable";
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
      setHealthState("Ready", "ready");
      return;
    }

    setHealthState("Unhealthy", "error");
  } catch (_) {
    setHealthState("Unavailable", "error");
    setError("Hermes API is not reachable yet.");
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
  return payload?.choices?.[0]?.message?.content?.trim() || "Hermes returned no visible text.";
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
    appendMessage("assistant", "The request failed before Hermes could answer.");
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
  await loadModels();
  await checkHealth();
}

init();