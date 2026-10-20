// Utilidades compartilhadas: formatação, API, diálogos, avisos e markdown.

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

// ── Formatação (pt-BR) ──────────────────────────────────

const brlFmt = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const pctFmt = new Intl.NumberFormat("pt-BR", { style: "percent", maximumFractionDigits: 0 });

// "Ocultar valores": todo valor em dinheiro do app passa por estas funções, então basta
// mascarar aqui. Cotações de ativos (money) continuam visíveis: não são dados pessoais.
let hideValues = false;
export const setHideValues = (on) => { hideValues = Boolean(on); };
export const valuesHidden = () => hideValues;
const MASK = "R$ ••••";

export const brl = (v) => (hideValues ? MASK : brlFmt.format(v ?? 0));
export const pct = (v) => pctFmt.format(v ?? 0);
export const money = (v, currency = "BRL") =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: currency || "BRL" }).format(v ?? 0);
export const moneyCompact = (v, currency = "BRL") =>
  new Intl.NumberFormat("pt-BR", {
    style: "currency", currency: currency || "BRL", notation: "compact", maximumFractionDigits: 1,
  }).format(v ?? 0);
// Eixos dos gráficos de finanças pessoais (mascarado como brl)
export const brlCompact = (v) => (hideValues ? "••••" : moneyCompact(v));
export const num = (v, digits = 2) =>
  (v ?? 0).toLocaleString("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits });
export const compactNum = (v) =>
  new Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: 1 }).format(v ?? 0);

export const monthName = (y, m) =>
  new Intl.DateTimeFormat("pt-BR", { month: "long" }).format(new Date(y, m - 1, 1));
export const monthTitle = (y, m) => {
  const n = monthName(y, m);
  return `${n[0].toUpperCase()}${n.slice(1)} de ${y}`;
};
export const shortDate = (iso) =>
  new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short" })
    .format(new Date(String(iso).slice(0, 10) + "T12:00:00")).replace(".", "");
export const fullDate = (iso) =>
  new Intl.DateTimeFormat("pt-BR").format(new Date(String(iso).slice(0, 10) + "T12:00:00"));
export const isoDate = (iso) => (iso ? String(iso).slice(0, 10) : "");
export const todayIso = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

// Variação com seta: verde/vermelho nunca aparecem sem ▲/▼
export function changeHtml(v, digits = 2) {
  if (v == null || Number.isNaN(v)) return "—";
  const up = v >= 0;
  return `<span class="change ${up ? "up" : "down"}">${up ? "▲" : "▼"} ${num(Math.abs(v), digits)}%</span>`;
}

export function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

export const icon = (name, label = "") =>
  `<svg ${label ? `aria-label="${esc(label)}" role="img"` : 'aria-hidden="true"'}><use href="#i-${name}"/></svg>`;

// ── API ─────────────────────────────────────────────────

// O app abre a janela com ?t=<token>. Guardamos na sessão e tiramos da barra de endereço.
const TOKEN = (() => {
  const url = new URL(location.href);
  const fromUrl = url.searchParams.get("t");
  if (fromUrl) {
    try { sessionStorage.setItem("stonks-token", fromUrl); } catch { /* sessão indisponível */ }
    url.searchParams.delete("t");
    history.replaceState(null, "", url.pathname + url.search + url.hash);
    return fromUrl;
  }
  try { return sessionStorage.getItem("stonks-token") || ""; } catch { return ""; }
})();

const authHeaders = (extra = {}) => (TOKEN ? { ...extra, "X-Stonks-Token": TOKEN } : extra);

function detailMessage(body, status) {
  const d = body && body.detail;
  if (Array.isArray(d)) return d.map((e) => e.msg).join("; ");
  return d || `Erro ${status}`;
}

export async function api(path, { method = "GET", body, raw } = {}) {
  const init = { method, headers: authHeaders() };
  if (raw !== undefined) {
    init.body = raw;
  } else if (body !== undefined) {
    init.body = JSON.stringify(body);
    init.headers["Content-Type"] = "application/json";
  }
  const res = await fetch(path, init);
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (res.status === 423) window.dispatchEvent(new Event("stonks:locked"));
  if (!res.ok) throw new Error(detailMessage(data, res.status));
  return data;
}

// Resposta da IA chegando aos poucos; onText recebe o texto acumulado
export async function apiStream(path, { method = "GET", body, signal, onText }) {
  const init = { method, signal, headers: authHeaders() };
  if (body !== undefined) {
    init.body = JSON.stringify(body);
    init.headers["Content-Type"] = "application/json";
  }
  const res = await fetch(path, init);
  if (!res.ok) {
    if (res.status === 423) window.dispatchEvent(new Event("stonks:locked"));
    const data = await res.json().catch(() => ({}));
    throw new Error(detailMessage(data, res.status));
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let text = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    text += decoder.decode(value, { stream: true });
    onText(text);
  }
  return text;
}

// ── Avisos (toast) ──────────────────────────────────────

export function toast(message, kind = "ok") {
  const region = $("#toasts");
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.textContent = message;
  region.append(el);
  setTimeout(() => el.remove(), kind === "error" ? 7000 : 3500);
}

// ── Diálogos ────────────────────────────────────────────

function buildDialog(inner) {
  const dlg = document.createElement("dialog");
  dlg.className = "form-dialog";
  dlg.innerHTML = inner;
  document.body.append(dlg);
  dlg.addEventListener("close", () => dlg.remove());
  dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
  return dlg;
}

export function confirmDialog({ title, message, confirmLabel, danger = true }) {
  return new Promise((resolve) => {
    const dlg = buildDialog(`
      <form method="dialog">
        <h2>${esc(title)}</h2>
        <p class="muted">${esc(message)}</p>
        <div class="dialog-actions">
          <button class="btn" value="cancel">Cancelar</button>
          <button class="btn ${danger ? "btn-danger" : "btn-primary"}" value="ok">${esc(confirmLabel)}</button>
        </div>
      </form>`);
    dlg.addEventListener("close", () => resolve(dlg.returnValue === "ok"));
    dlg.showModal();
  });
}

function fieldHtml(f) {
  const id = `f-${f.name}`;
  const req = f.required ? "required" : "";
  const value = f.value ?? "";
  if (f.type === "select") {
    const opts = f.options.map((o) => {
      const [val, label] = Array.isArray(o) ? o : [o, o];
      return `<option value="${esc(val)}" ${String(val) === String(value) ? "selected" : ""}>${esc(label)}</option>`;
    }).join("");
    return `<label class="field" for="${id}"><span>${esc(f.label)}</span><select id="${id}" name="${f.name}" ${req}>${opts}</select></label>`;
  }
  if (f.type === "textarea") {
    return `<label class="field" for="${id}"><span>${esc(f.label)}</span><textarea id="${id}" name="${f.name}" rows="3">${esc(value)}</textarea></label>`;
  }
  if (f.type === "segmented") {
    const opts = f.options.map(([val, label]) => `
      <label><input type="radio" name="${f.name}" value="${esc(val)}" ${String(val) === String(value) ? "checked" : ""}><span>${esc(label)}</span></label>`).join("");
    return `<div class="field" role="radiogroup" aria-labelledby="${id}"><span id="${id}">${esc(f.label)}</span><div class="seg">${opts}</div></div>`;
  }
  const extra = [
    f.step ? `step="${f.step}"` : "", f.min != null ? `min="${f.min}"` : "",
    f.placeholder ? `placeholder="${esc(f.placeholder)}"` : "", f.autofocus ? "autofocus" : "",
  ].join(" ");
  return `<label class="field" for="${id}"><span>${esc(f.label)}</span>
    <input id="${id}" name="${f.name}" type="${f.type || "text"}" value="${esc(value)}" ${req} ${extra}></label>`;
}

// Formulário em diálogo. onSubmit recebe os valores; se lançar erro, ele aparece no próprio diálogo.
export function formDialog({ title, fields, submitLabel, onSubmit }) {
  return new Promise((resolve) => {
    const dlg = buildDialog(`
      <form novalidate>
        <h2>${esc(title)}</h2>
        <div class="form-grid">${fields.map(fieldHtml).join("")}</div>
        <p class="form-error" role="alert" hidden></p>
        <div class="dialog-actions">
          <button type="button" class="btn" data-cancel>Cancelar</button>
          <button type="submit" class="btn btn-primary">${esc(submitLabel)}</button>
        </div>
      </form>`);
    const form = $("form", dlg);
    const err = $(".form-error", dlg);
    let result = null;
    $("[data-cancel]", dlg).addEventListener("click", () => dlg.close());
    dlg.addEventListener("close", () => resolve(result));
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!form.reportValidity()) return;
      const values = Object.fromEntries(new FormData(form).entries());
      const btn = $("button[type=submit]", form);
      btn.disabled = true;
      err.hidden = true;
      try {
        result = await onSubmit(values);
        dlg.close();
      } catch (ex) {
        err.textContent = ex.message;
        err.hidden = false;
      } finally {
        btn.disabled = false;
      }
    });
    dlg.showModal();
    const first = $("[autofocus]", dlg) || $("input, select, textarea", dlg);
    if (first) first.focus();
  });
}

// ── Markdown simples e seguro (o texto é escapado antes) ─

function inline(s) {
  return s
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>");
}

export function markdown(src) {
  // Respostas da IA citam valores do usuário; com "ocultar valores" eles também somem
  if (hideValues) src = String(src ?? "").replace(/R\$\s?-?[\d.]+(?:,\d+)?/g, MASK);
  const lines = esc(src).split(/\r?\n/);
  let html = "";
  let para = [];
  let list = null;
  let table = [];
  const flushPara = () => { if (para.length) { html += `<p>${inline(para.join(" "))}</p>`; para = []; } };
  const closeList = () => { if (list) { html += `</${list}>`; list = null; } };
  const flushTable = () => {
    if (!table.length) return;
    const rows = table.filter((r) => !/^\|?[\s:|-]+\|?$/.test(r))
      .map((r) => r.replace(/^\||\|$/g, "").split("|").map((c) => inline(c.trim())));
    const [head, ...body] = rows;
    html += `<div class="md-table"><table><thead><tr>${head.map((c) => `<th>${c}</th>`).join("")}</tr></thead>
      <tbody>${body.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
    table = [];
  };
  for (const raw of lines) {
    const line = raw.trim();
    let m;
    if (line.startsWith("|")) { flushPara(); closeList(); table.push(line); continue; }
    flushTable();
    if (!line) { flushPara(); closeList(); continue; }
    if ((m = line.match(/^(#{1,4})\s+(.*)$/))) {
      flushPara(); closeList();
      html += `<h3>${inline(m[2])}</h3>`;
    } else if ((m = line.match(/^[-*•]\s+(.*)$/))) {
      flushPara();
      if (list !== "ul") { closeList(); html += "<ul>"; list = "ul"; }
      html += `<li>${inline(m[1])}</li>`;
    } else if ((m = line.match(/^\d+[.)]\s+(.*)$/))) {
      flushPara();
      if (list !== "ol") { closeList(); html += "<ol>"; list = "ol"; }
      html += `<li>${inline(m[1])}</li>`;
    } else {
      closeList();
      para.push(line);
    }
  }
  flushTable(); flushPara(); closeList();
  return html;
}

// ── Caixa de resposta da IA (streaming) ─────────────────
// Liga um botão a uma rota de streaming e mostra o texto em markdown conforme chega.

export function aiPanel(container, { label, path, body, method, emptyHint }) {
  container.innerHTML = `
    <div class="ai-panel">
      <div class="ai-head">
        <button class="btn" type="button" data-run>${icon("sparkle")}<span>${esc(label)}</span></button>
        ${emptyHint ? `<p class="muted small">${esc(emptyHint)}</p>` : ""}
      </div>
      <div class="ai-output md" aria-live="polite" hidden></div>
    </div>`;
  const btn = $("[data-run]", container);
  const out = $(".ai-output", container);
  let controller = null;

  btn.addEventListener("click", async () => {
    if (controller) { controller.abort(); return; }
    controller = new AbortController();
    btn.lastElementChild.textContent = "Parar";
    out.hidden = false;
    out.classList.add("streaming");
    out.innerHTML = `<p class="muted">A IA está escrevendo…</p>`;
    try {
      await apiStream(typeof path === "function" ? path() : path, {
        method: method || (body ? "POST" : "GET"),
        body: typeof body === "function" ? body() : body,
        signal: controller.signal,
        onText: (t) => { out.innerHTML = markdown(t); },
      });
      out.insertAdjacentHTML("beforeend",
        `<p class="ai-note">Gerado por IA a partir dos dados exibidos. Não é recomendação de investimento.</p>`);
    } catch (e) {
      if (e.name !== "AbortError") out.innerHTML = `<p class="form-error">${esc(e.message)}</p>`;
    } finally {
      controller = null;
      out.classList.remove("streaming");
      btn.lastElementChild.textContent = label;
    }
  });
}

export function emptyState(message) {
  return `<p class="empty">${message}</p>`;
}
