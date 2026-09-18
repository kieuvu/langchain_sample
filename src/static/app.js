document.addEventListener("DOMContentLoaded", () => {
  const messagesContainer = document.querySelector("#messages-container");
  const emptyState = document.querySelector("#empty-state");
  const form = document.querySelector("#chat-form");
  const input = document.querySelector("#user-input");
  const sendButton = document.querySelector("#send-btn");
  const statusPill = document.querySelector("#status-pill");
  const statusText = document.querySelector("#status-text");

  let sessionId = null;
  let busy = false;

  function updateInputState() {
    input.disabled = busy || !sessionId;
    const hasText = Boolean(input.value.trim());
    sendButton.disabled = busy || !sessionId || !hasText;
    resizeTextarea();
  }

  function resizeTextarea() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 160) + "px";
  }

  function setStatus(label, state = "ready") {
    statusText.textContent = label;
    statusPill.className = "status-pill";
    if (state === "connecting") statusPill.classList.add("connecting");
    else if (state === "busy") statusPill.classList.add("busy");
    else if (state === "error") statusPill.classList.add("error");
  }

  function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function appendMessage(role, text = "") {
    emptyState.hidden = true;
    const item = document.createElement("div");
    item.className = `message-item ${role}`;

    const bubbleContainer = document.createElement("div");
    bubbleContainer.className = "bubble-container";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.textContent = text;

    bubbleContainer.append(bubble);
    item.append(bubbleContainer);
    messagesContainer.append(item);
    scrollToBottom();
    return { bubble, bubbleContainer };
  }

  function finishActiveBadge(bubbleContainer) {
    const badge = bubbleContainer.querySelector(".tool-call-badge.active");
    if (!badge) return;
    badge.classList.remove("active");
    badge.textContent = `✓ ${badge.dataset.completedLabel}`;
  }

  function showProgress(bubbleContainer, bubble, label, completedLabel, streamState) {
    finishActiveBadge(bubbleContainer);
    const badge = document.createElement("div");
    badge.className = "tool-call-badge active";
    badge.dataset.completedLabel = completedLabel;
    const spinner = document.createElement("div");
    spinner.className = "tool-spin";
    badge.append(spinner, document.createTextNode(label));
    bubbleContainer.insertBefore(badge, bubble);
    if (!streamState.hasToken) bubble.textContent = label;
    setStatus(label, "busy");
    scrollToBottom();
  }

  // Always create a fresh session for this page load (refresh = new session)
  async function initSession() {
    busy = true;
    updateInputState();
    setStatus("Connecting...", "connecting");

    try {
      const res = await fetch("/v1/sessions", { method: "POST" });
      if (!res.ok) throw new Error("Could not initialize chat session.");
      const data = await res.json();
      sessionId = data.session_id;
      setStatus(`Ready`, "ready");
      input.focus();
    } catch (err) {
      setStatus(err.message || "Failed to connect", "error");
    } finally {
      busy = false;
      updateInputState();
    }
  }

  function parseEvent(block, bubble, bubbleContainer, streamState) {
    const lines = block.replace(/\r/g, "").split("\n");
    const event = lines.find((l) => l.startsWith("event: "))?.slice(7);
    const dataStr = lines.filter((l) => l.startsWith("data: ")).map((l) => l.slice(6)).join("\n");
    if (!event || !dataStr) return;

    let payload;
    try {
      payload = JSON.parse(dataStr);
    } catch {
      return;
    }

    if (event === "progress") {
      const steps = {
        router_agent: ["Thinking: choosing how to help...", "Route chosen"],
        weather_agent: ["Running: weather assistant...", "Weather assistant finished"],
        general_agent: ["Running: assistant...", "Assistant finished"],
      };
      const step = steps[payload.step];
      if (step) showProgress(bubbleContainer, bubble, step[0], step[1], streamState);
    } else if (event === "token") {
      if (!streamState.hasToken) {
        bubble.textContent = "";
        streamState.hasToken = true;
        bubble.dataset.hasToken = "true";
      }
      bubble.textContent += payload.text || "";
      scrollToBottom();
    } else if (event === "tool_start") {
      const tool = payload.name;
      const loc = payload.input?.location ? ` (${payload.input.location})` : "";
      showProgress(bubbleContainer, bubble, `Running: ${tool}${loc}`, `Completed: ${tool}`, streamState);
    } else if (event === "tool_end") {
      finishActiveBadge(bubbleContainer);
      if (!streamState.hasToken) bubble.textContent = "Generating reply...";
      setStatus("Generating reply...", "busy");
    } else if (event === "done") {
      finishActiveBadge(bubbleContainer);
      bubble.textContent = payload.answer || "";
      streamState.done = true;
      setStatus("Ready", "ready");
      scrollToBottom();
    } else if (event === "error") {
      streamState.error = payload.message || "Error processing message";
    }
  }

  async function streamReply(message, bubble, bubbleContainer) {
    const res = await fetch(`/v1/sessions/${encodeURIComponent(sessionId)}/messages/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });

    if (!res.ok) throw new Error("Could not process message.");
    if (!res.body) throw new Error("Browser does not support streaming.");

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    const streamState = { done: false, error: null, hasToken: false };
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
      let boundary;
      while ((boundary = buffer.indexOf("\n\n")) !== -1) {
        parseEvent(buffer.slice(0, boundary), bubble, bubbleContainer, streamState);
        buffer = buffer.slice(boundary + 2);
      }
    }

    buffer += decoder.decode();
    if (buffer.trim()) parseEvent(buffer, bubble, bubbleContainer, streamState);
    if (streamState.error) throw new Error(streamState.error);
    if (!streamState.done) throw new Error("Stream closed prematurely.");
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = input.value.trim();
    if (!message || !sessionId || busy) return;

    input.value = "";
    updateInputState();
    appendMessage("user", message);

    const { bubble, bubbleContainer } = appendMessage("assistant", "Thinking...");
    busy = true;
    updateInputState();
    setStatus("Thinking...", "busy");

    try {
      await streamReply(message, bubble, bubbleContainer);
      setStatus("Ready", "ready");
    } catch (err) {
      const activeBadge = bubbleContainer.querySelector(".tool-call-badge.active");
      if (activeBadge) {
        activeBadge.classList.remove("active");
        activeBadge.textContent = "✕ Step failed";
      }
      bubble.textContent = bubble.dataset.hasToken
        ? `${bubble.textContent}\n\n[Error: ${err.message}]`
        : err.message;
      bubble.classList.add("error");
      setStatus("Error", "error");
    } finally {
      busy = false;
      updateInputState();
      input.focus();
    }
  });

  input.addEventListener("input", updateInputState);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  document.querySelectorAll("[data-prompt]").forEach((btn) => {
    btn.addEventListener("click", () => {
      input.value = btn.dataset.prompt;
      updateInputState();
      input.focus();
    });
  });

  initSession();
});
