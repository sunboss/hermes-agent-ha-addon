const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const sendButton = document.getElementById("send-button");
const errorMessage = document.getElementById("error-message");
const messageTemplate = document.getElementById("message-template");
const healthStatus = document.getElementById("health-status");
const conversationId = document.getElementById("conversation-id");
const resetButton = document.getElementById("reset-chat");

const conversationStorageKey = "hermes-ingress-conversation";
let currentConversation = localStorage.getItem(conversationStorageKey) || crypto.randomUUID();
let messages = [];
let activeModel = "hermes-agent";

conversationId.textContent = currentConversation.slice(0, 8);

function setError(message = "") {
  if (!message) {
    errorMessage.hidden = true;
    errorMessage.textContent = "";
    return;
  }
  errorMessage.hidden = false;
  errorMessage.textContent = message;
}

function appendMessage(role, content) {
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
  chatLog.innerHTML = "";
  setError();
}

async function loadModels() {
  try {
    const response = await fetch("./api/v1/models");
    if (!response.ok) {
      return;
    }
    const data = await response.json();
    if (Array.isArray(data.data) && data.data.length > 0 && data.data[0].id) {
      activeModel = data.data[0].id;
    }
  } catch (_) {
    // Fall back to the default shim model name.
  }
}

async function checkHealth() {
  try {
    const response = await fetch("./api/health");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    healthStatus.textContent = data.status === "ok" ? "Ready" : "Unhealthy";
  } catch (error) {
    healthStatus.textContent = "Unavailable";
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
  if (!text) return;

  setError();
  sendButton.disabled = true;
  appendMessage("user", text);
  chatInput.value = "";

  try {
    const payload = await sendMessage(text);
    const assistantText = extractAssistantText(payload);
    messages.push({ role: "user", content: text }, { role: "assistant", content: assistantText });
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

resetButton.addEventListener("click", resetConversation);

async function init() {
  await loadModels();
  await checkHealth();
}

init();
