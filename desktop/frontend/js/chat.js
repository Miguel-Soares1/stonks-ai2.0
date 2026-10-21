// Conversa com a IA, compartilhada pela tela Assistente e pelo painel flutuante.
// A conversa é uma só: o que foi dito num lugar aparece no outro.

import { apiStream, esc, icon, markdown, $ } from "./core.js";

const SUGGESTIONS = [
  "Quanto está a PETR4 agora?",
  "Quanto gastei este mês?",
  "O que é P/L e como interpretar?",
  "Como montar uma reserva de emergência?",
];

// O servidor marca entre \x1e o que a IA consultou ("cotação de PETR4", ADR 026). Essas
// marcas viram uma linha à parte e não entram no texto que volta para a IA como histórico.
const MARK = "\x1e";
function splitStatus(raw) {
  const parts = raw.split(MARK);
  return { content: parts.filter((_, i) => i % 2 === 0).join(""), tools: parts.filter((_, i) => i % 2 === 1) };
}

function toolNote(m, writing) {
  if (!m.tools || !m.tools.length) return "";
  const list = [...new Set(m.tools)].join(", ");
  return `<p class="tool-note">${icon("search")}<span>${writing && !m.content ? `Consultando ${esc(list)}…` : `Consultei: ${esc(list)}`}</span></p>`;
}

// Valor em reais sem nenhuma consulta: pode ser exemplo didático, ou um número que o modelo inventou
const MONEY = /R\$\s?\d/;
function unverifiedNote(m, writing) {
  if (writing || (m.tools && m.tools.length) || !MONEY.test(m.content)) return "";
  return `<p class="tool-note">${icon("alert")}<span>Valores sem consulta aos dados do app: podem ser só exemplos.</span></p>`;
}

function assistantHtml(m, writing = false) {
  return toolNote(m, writing) + (markdown(m.content) || (writing || !m.tools?.length ? '<p class="muted">Escrevendo…</p>' : ""))
    + unverifiedNote(m, writing);
}

const history = [];
let controller = null;
const mounted = new Set(); // cada lugar onde a conversa está aberta

export function mountChat(root, { compact = false } = {}) {
  root.innerHTML = `
    <div class="chat ${compact ? "chat-compact" : ""}">
      <div class="chat-log" aria-live="polite"></div>
      <form class="chat-input">
        <textarea name="message" rows="2" placeholder="Pergunte uma cotação, quanto gastou no mês ou tire uma dúvida" aria-label="Mensagem" required></textarea>
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
          <p>Pergunte cotações e indicadores, quanto você gastou, como está a sua carteira, as metas e o orçamento, ou tire dúvidas sobre investimentos.</p>
          <div class="chips">${SUGGESTIONS.map((s) => `<button class="chip" type="button">${esc(s)}</button>`).join("")}</div>
        </div>`;
      v.log.querySelectorAll(".chip").forEach((c) => c.addEventListener("click", () => send(c.textContent)));
      continue;
    }
    v.log.innerHTML = history.map((m) => `
      <div class="msg ${m.role}">
        <div class="bubble ${m.role === "assistant" ? "md" : ""}">${m.role === "assistant" ? assistantHtml(m, m === writingNow) : esc(m.content)}</div>
      </div>`).join("");
    v.log.scrollTop = v.log.scrollHeight;
  }
}

let writingNow = null;

async function send(text) {
  history.push({ role: "user", content: text });
  const answer = { role: "assistant", content: "", tools: [] };
  history.push(answer);
  writingNow = answer;
  paint();

  const mine = new AbortController();
  controller = mine;
  setBusy(true);
  try {
    await apiStream("/api/chat", {
      method: "POST",
      // Só papel e texto: as ferramentas consultadas não voltam como histórico
      body: { messages: history.slice(0, -1).map(({ role, content }) => ({ role, content })) },
      signal: mine.signal,
      onText: (t) => {
        Object.assign(answer, splitStatus(t));
        for (const v of live()) {
          const last = [...v.log.querySelectorAll(".msg.assistant .bubble")].at(-1);
          if (last) { last.innerHTML = assistantHtml(answer, true); v.log.scrollTop = v.log.scrollHeight; }
        }
      },
    });
  } catch (e) {
    if (e.name !== "AbortError") answer.content = `**Não foi possível responder:** ${e.message}`;
  } finally {
    writingNow = null;
    const i = history.indexOf(answer);
    if (!answer.content && i > 0) history.splice(i - 1, 2);
    if (controller === mine) { controller = null; setBusy(false); }
    paint();
  }
}
