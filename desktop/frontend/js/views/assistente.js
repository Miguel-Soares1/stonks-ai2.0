// Assistente: conversa com a IA, com a resposta aparecendo enquanto é escrita.

import { apiStream, esc, icon, markdown, $ } from "../core.js";

const SUGGESTIONS = [
  "O que é P/L e como interpretar?",
  "Qual a diferença entre CDB e Tesouro Direto?",
  "Como montar uma reserva de emergência?",
  "O que são FIIs?",
];

// A conversa continua ao trocar de tela e voltar
const history = [];
let controller = null;

export async function render(root) {
  root.innerHTML = `
    <div class="page-head">
      <h1 class="page-title">Conversar com a IA</h1>
      <button class="btn" type="button" id="new-chat">Nova conversa</button>
    </div>
    <div class="chat">
      <div class="chat-log" id="log" aria-live="polite"></div>
      <form class="chat-input" id="chat-form">
        <textarea name="message" rows="2" placeholder="Pergunte sobre investimentos, indicadores ou finanças pessoais" aria-label="Mensagem" required></textarea>
        <button class="btn btn-primary" type="submit" id="send">${icon("send")}<span>Enviar</span></button>
      </form>
      <p class="muted small">As respostas são geradas por IA e podem conter erros. Não são recomendação de investimento.</p>
    </div>`;

  const form = $("#chat-form", root);
  const input = $("textarea", form);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
  });
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    if (controller) { controller.abort(); return; }
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    send(root, text);
  });
  $("#new-chat", root).addEventListener("click", () => {
    if (controller) controller.abort();
    history.length = 0;
    paint(root);
    input.focus();
  });
  paint(root);
  input.focus();
}

function paint(root) {
  const log = $("#log", root);
  if (!history.length) {
    log.innerHTML = `
      <div class="chat-empty">
        <p>Tire dúvidas sobre mercado, indicadores, renda fixa ou organização financeira.</p>
        <div class="chips">${SUGGESTIONS.map((s) => `<button class="chip" type="button">${esc(s)}</button>`).join("")}</div>
      </div>`;
    log.querySelectorAll(".chip").forEach((c) => c.addEventListener("click", () => send(root, c.textContent)));
    return;
  }
  log.innerHTML = history.map((m) => `
    <div class="msg ${m.role}">
      <div class="bubble ${m.role === "assistant" ? "md" : ""}">${m.role === "assistant" ? markdown(m.content) || '<p class="muted">Escrevendo…</p>' : esc(m.content)}</div>
    </div>`).join("");
  log.scrollTop = log.scrollHeight;
}

async function send(root, text) {
  history.push({ role: "user", content: text });
  const answer = { role: "assistant", content: "" };
  history.push(answer);
  paint(root);

  const sendBtn = $("#send", root);
  controller = new AbortController();
  sendBtn.lastElementChild.textContent = "Parar";
  const bubbles = () => root.querySelectorAll(".msg.assistant .bubble");
  try {
    await apiStream("/api/chat", {
      method: "POST",
      body: { messages: history.slice(0, -1) },
      signal: controller.signal,
      onText: (t) => {
        answer.content = t;
        const last = [...bubbles()].at(-1);
        if (last) {
          last.innerHTML = markdown(t);
          $("#log", root).scrollTop = $("#log", root).scrollHeight;
        }
      },
    });
  } catch (e) {
    if (e.name !== "AbortError") answer.content = `**Não foi possível responder:** ${e.message}`;
  } finally {
    if (!answer.content) history.splice(-2, 2);
    controller = null;
    if (root.isConnected) {
      sendBtn.lastElementChild.textContent = "Enviar";
      paint(root);
    }
  }
}
