const terminalText = {
  eyebrow: "Hermes Native Shell",
  title: "\u547d\u4ee4\u884c\u5de5\u4f5c\u53f0",
  copy: "\u8fd9\u4e2a\u9762\u677f\u76f4\u63a5\u627f\u8f7d\u5b8c\u6574 ttyd \u7ec8\u7aef\uff0c\u9002\u5408\u8fd0\u884c bash\u3001Hermes CLI \u548c\u5bb9\u5668\u5185\u914d\u7f6e\u547d\u4ee4\u3002\u624b\u673a\u7aef\u4f1a\u81ea\u52a8\u538b\u7f29\u5934\u90e8\uff0c\u8ba9\u7ec8\u7aef\u5c3d\u91cf\u5403\u6ee1\u5c4f\u5e55\u3002",
  back: "\u8fd4\u56de\u63a7\u5236\u53f0",
  open: "\u65b0\u7a97\u53e3\u6253\u5f00",
  reload: "\u5237\u65b0\u7ec8\u7aef",
  stack: "ttyd / xterm.js",
  cardTitle: "\u539f\u751f\u98ce\u683c\u547d\u4ee4\u884c",
  hint: "\u5efa\u8bae\u6a2a\u5c4f\u6216\u5c55\u5f00\u5168\u5c4f\u4f7f\u7528\u3002\u89e6\u63a7\u6eda\u52a8\u3001\u8f93\u5165\u6cd5\u548c\u79fb\u52a8\u7aef\u5e03\u5c40\u90fd\u4f18\u5148\u7167\u987e\u5b9e\u9645\u64cd\u4f5c\u4f53\u9a8c\u3002",
};

const frame = document.getElementById("terminal-frame");
const reloadButton = document.getElementById("reload-terminal");

function applyTerminalText() {
  document.title = terminalText.title;
  document.getElementById("terminal-eyebrow").textContent = terminalText.eyebrow;
  document.getElementById("terminal-page-title").textContent = terminalText.title;
  document.getElementById("terminal-page-copy").textContent = terminalText.copy;
  document.getElementById("terminal-back").textContent = terminalText.back;
  document.getElementById("terminal-open").textContent = terminalText.open;
  document.getElementById("reload-terminal").textContent = terminalText.reload;
  document.getElementById("terminal-stack-label").textContent = terminalText.stack;
  document.getElementById("terminal-card-title").textContent = terminalText.cardTitle;
  document.getElementById("terminal-hint").textContent = terminalText.hint;
}

function reloadTerminal() {
  if (!frame) {
    return;
  }
  const current = frame.getAttribute("src") || "./ttyd/";
  const next = current.includes("?") ? `${current.split("?")[0]}?t=${Date.now()}` : `${current}?t=${Date.now()}`;
  frame.setAttribute("src", next);
}

applyTerminalText();

if (reloadButton) {
  reloadButton.addEventListener("click", reloadTerminal);
}