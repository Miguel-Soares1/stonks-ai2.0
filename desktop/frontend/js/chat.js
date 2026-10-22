// Conversa com a IA, compartilhada pela tela Assistente e pelo painel flutuante.
// A conversa é uma só: o que foi dito num lugar aparece no outro.

import { api, apiStream, brl, esc, icon, markdown, money, toast, $ } from "./core.js";

const SUGGESTIONS = [
  "Quanto está a PETR4 agora?",
  "Quanto gastei este mês?",
  "Gastei 45 reais no iFood hoje",
  "O que é P/L e como interpretar?",
  "Como montar uma reserva de emergência?",
];

// O servidor marca entre \x1e o que a IA consultou ("cotação de PETR4", ADR 026). Essas
// marcas viram uma linha à parte e não entram no texto que volta para a IA como histórico.
const MARK = "\x1e";
// Propostas de lançamento vêm em JSON entre \x1d (ADR 027): a IA só prepara, quem grava é o
// botão Confirmar, pelas mesmas rotas das telas.
const PROPOSAL = "\x1d";
function splitStatus(raw) {
  const chunks = raw.split(PROPOSAL);
  if (chunks.length % 2 === 0) chunks.pop(); // proposta ainda chegando
  const proposals = [];
  for (let i = 1; i < chunks.length; i += 2) {
    try { proposals.push(JSON.parse(chunks[i])); } catch { /* ignora uma proposta quebrada */ }
  }
  const parts = chunks.filter((_, i) => i % 2 === 0).join("").split(MARK);
  return { content: parts.filter((_, i) => i % 2 === 0).join(""), tools: parts.filter((_, i) => i % 2 === 1), proposals };
}

// Para onde vai cada proposta confirmada (a tela decide a rota, não a IA)
const ENDPOINTS = {
  transacao: () => "/api/transactions",
  meta: (p) => `/api/goals/${Number(p.id)}/contribute`,
  watchlist: () => "/api/watchlist",
};

function cell([, value, currency]) {
  if (!currency || typeof value !== "number") return esc(value);
  return esc(currency === "BRL" ? brl(value) : money(value, currency));
}

function proposalHtml(p, mi, i, state, writing) {
  const rows = p.linhas.map((r) => `<dt>${esc(r[0])}</dt><dd>${cell(r)}</dd>`).join("");
  let foot;
  if (state?.s === "ok") foot = `<p class="proposal-status ok">${icon("check")}<span>${esc(p.feito)}</span></p>`;
  else if (state?.s === "cancel") foot = `<p class="proposal-status">Cancelado. Nada foi lançado.</p>`;
  else {
    const off = writing || state?.s === "busy" ? "disabled" : "";
    foot = `${state?.s === "error" ? `<p class="proposal-status error">${icon("alert")}<span>${esc(state.msg)}</span></p>` : ""}
      <div class="proposal-actions">
        <button class="btn btn-primary btn-sm" type="button" data-confirm data-msg="${mi}" data-i="${i}" ${off}>${icon("check")}<span>Confirmar</span></button>
        <button class="btn btn-sm" type="button" data-cancel data-msg="${mi}" data-i="${i}" ${off}>Cancelar</button>
      </div>`;
  }
  return `<div class="proposal"><p class="proposal-title">${esc(p.titulo)}</p><dl>${rows}</dl>${foot}</div>`;
}

function proposalsHtml(m, mi, writing) {
  return (m.proposals || []).map((p, i) => proposalHtml(p, mi, i, m.states?.[i], writing)).join("");
}

function toolNote(m, writing) {
  if (!m.tools || !m.tools.length) return "";
  const list = [...new Set(m.tools)].join(", ");
  return `<p class="tool-note">${icon("search")}<span>${writing && !m.content ? `Consultando ${esc(list)}…` : `Consultei: ${esc(list)}`}</span></p>`;
}

// O modelo diz que preparou um lançamento, mas não chamou a ferramenta: não há o que confirmar
const CLAIMS_PROPOSAL = /confirm/i;
function missingProposalNote(m, writing) {
  if (writing || m.proposals?.length || !CLAIMS_PROPOSAL.test(m.content)) return "";
  return `<p class="tool-note">${icon("alert")}<span>Nenhum lançamento foi preparado. Peça de novo ou lance pela tela.</span></p>`;
}

// Valor em reais sem nenhuma consulta: pode ser exemplo didático, ou um número que o modelo inventou
const MONEY = /R\$\s?\d/;
function unverifiedNote(m, writing) {
  if (writing || m.tools?.length || m.proposals?.length || !MONEY.test(m.content)) return "";
  return `<p class="tool-note">${icon("alert")}<span>Valores sem consulta aos dados do app: podem ser só exemplos.</span></p>`;
}

function assistantHtml(m, mi, writing = false) {
  const empty = writing || !(m.tools?.length || m.proposals?.length);
  return toolNote(m, writing) + (markdown(m.content) || (empty ? '<p class="muted">Escrevendo…</p>' : ""))
    + proposalsHtml(m, mi, writing) + (missingProposalNote(m, writing) || unverifiedNote(m, writing));
}

async function decide(mi, i, confirmed) {
  const m = history[mi];
  const p = m?.proposals?.[i];
  if (!p || !ENDPOINTS[p.tipo]) return;
  m.states = m.states || {};
  if (!confirmed) { m.states[i] = { s: "cancel" }; paint(); return; }
  m.states[i] = { s: "busy" };
  paint();
  try {
    await api(ENDPOINTS[p.tipo](p), { method: "POST", body: p.corpo });
    m.states[i] = { s: "ok" };
    toast(p.feito);
    window.dispatchEvent(new Event("stonks:changed")); // a tela aberta atrás mostra o lançamento
  } catch (e) {
    m.states[i] = { s: "error", msg: e.message };
  }
  paint();
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
  view.log.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-confirm], [data-cancel]");
    if (btn) decide(Number(btn.dataset.msg), Number(btn.dataset.i), btn.hasAttribute("data-confirm"));
  });

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
    v.log.innerHTML = history.map((m, mi) => `
      <div class="msg ${m.role}">
        <div class="bubble ${m.role === "assistant" ? "md" : ""}">${m.role === "assistant" ? assistantHtml(m, mi, m === writingNow) : esc(m.content)}</div>
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
          if (last) { last.innerHTML = assistantHtml(answer, history.indexOf(answer), true); v.log.scrollTop = v.log.scrollHeight; }
        }
      },
    });
  } catch (e) {
    if (e.name !== "AbortError") answer.content = `**Não foi possível responder:** ${e.message}`;
  } finally {
    writingNow = null;
    const i = history.indexOf(answer);
    if (!answer.content && !answer.proposals?.length && i > 0) history.splice(i - 1, 2);
    if (controller === mine) { controller = null; setBusy(false); }
    paint();
  }
}
