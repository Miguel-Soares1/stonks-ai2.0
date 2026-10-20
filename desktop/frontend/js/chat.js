// Conversa com a IA, compartilhada pela tela Assistente e pelo painel flutuante.
// A conversa é uma só: o que foi dito num lugar aparece no outro.

import { apiStream, esc, icon, markdown, $ } from "./core.js";

const SUGGESTIONS = [
  "O que é P/L e como interpretar?",
  "Qual a diferença entre CDB e Tesouro Direto?",
  "Como montar uma reserva de emergência?",
  "O que são FIIs?",
];

const history = [];
let controller = null;
const mounted = new Set(); // cada lugar onde a conversa está aberta

export function mountChat(root, { compact = false } = {}) {
  root.innerHTML = `
    <div class="chat ${compact ? "chat-compact" : ""}">
      <div class="chat-log" aria-live="polite"></div>
      <form class="chat-input">
        <textarea name="message" rows="2" placeholder="Pergunte sobre investimentos, indicadores ou finanças pessoais" aria-label="Mensagem" required></textarea>
        <button class="btn btn-primary" type="submit" data-send>${icon("send")}<span>Enviar</span></button>
      </form>
      <p class="muted small">As respostas são geradas por IA e podem conter erros. Não são recomendação de investimento.</p>
    </div>`;
  const view = { root, log: $(".chat-log", root), sendBtn: $("[data-send]", root), input: $("textarea", root) };
  mounted.add(view);

  const form = $("form", root);
  view.input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
  });
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    if (controller) { controller.abort(); return; }
    const text = view.input.value.trim();
    if (!text) return;
    view.input.value = "";
    send(text);
  });
  paint();
  setBusy(Boolean(controller));
  return { focus: () => view.input.focus() };
}

export function newChat() {
  if (controller) controller.abort();
  history.length = 0;
  paint();
}

// Abre a conversa já com uma pergunta (ex.: "Entender com a IA" num insight)
export function ask(text) {
  if (controller) controller.abort();
  send(text);
}

function live() {
  for (const v of mounted) if (!v.root.isConnected) mounted.delete(v);
  return [...mounted];
}

function setBusy(busy) {
  for (const v of live()) v.sendBtn.lastElementChild.textContent = busy ? "Parar" : "Enviar";
}

function paint() {
  for (const v of live()) {
    if (!history.length) {
      v.log.innerHTML = `
        <div class="chat-empty">
          <p>Tire dúvidas sobre mercado, indicadores, renda fixa ou organização financeira.</p>
          <div class="chips">${SUGGESTIONS.map((s) => `<button class="chip" type="button">${esc(s)}</button>`).join("")}</div>
        </div>`;
      v.log.querySelectorAll(".chip").forEach((c) => c.addEventListener("click", () => send(c.textContent)));
      continue;
    }
    v.log.innerHTML = history.map((m) => `
      <div class="msg ${m.role}">
        <div class="bubble ${m.role === "assistant" ? "md" : ""}">${m.role === "assistant" ? markdown(m.content) || '<p class="muted">Escrevendo…</p>' : esc(m.content)}</div>
      </div>`).join("");
    v.log.scrollTop = v.log.scrollHeight;
  }
}

async function send(text) {
  history.push({ role: "user", content: text });
  const answer = { role: "assistant", content: "" };
  history.push(answer);
  paint();

  const mine = new AbortController();
  controller = mine;
  setBusy(true);
  try {
    await apiStream("/api/chat", {
      method: "POST",
      body: { messages: history.slice(0, -1) },
      signal: mine.signal,
      onText: (t) => {
        answer.content = t;
        for (const v of live()) {
          const last = [...v.log.querySelectorAll(".msg.assistant .bubble")].at(-1);
          if (last) { last.innerHTML = markdown(t); v.log.scrollTop = v.log.scrollHeight; }
        }
      },
    });
  } catch (e) {
    if (e.name !== "AbortError") answer.content = `**Não foi possível responder:** ${e.message}`;
  } finally {
    const i = history.indexOf(answer);
    if (!answer.content && i > 0) history.splice(i - 1, 2);
    if (controller === mine) { controller = null; setBusy(false); }
    paint();
  }
}
