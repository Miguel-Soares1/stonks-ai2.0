// Orçamento: limite mensal por categoria e quanto já foi usado.

import { api, brl, esc, formDialog, icon, monthTitle, pct, toast, $ } from "../core.js";

const today = new Date();
const state = { year: today.getFullYear(), month: today.getMonth() + 1 };

// Status com rótulo em texto: a cor nunca é a única pista
const STATUS = {
  ok: ["Dentro do limite", "ok"],
  attention: ["Mais da metade usada", "ok"],
  warning: ["Perto do limite", "warn"],
  exceeded: ["Limite estourado", "bad"],
};

export async function render(root) {
  root.innerHTML = `
    <div class="month-nav">
      <h1 class="page-title">Orçamento</h1>
      <span class="month-title" id="month-title"></span>
      <div class="month-buttons">
        <button class="icon-btn" id="prev" type="button" aria-label="Mês anterior">${icon("left")}</button>
        <button class="icon-btn" id="next" type="button" aria-label="Próximo mês">${icon("right")}</button>
      </div>
    </div>
    <div id="budget" class="stack"></div>`;
  $("#prev", root).addEventListener("click", () => shift(root, -1));
  $("#next", root).addEventListener("click", () => shift(root, 1));
  load(root);
}

function shift(root, delta) {
  const d = new Date(state.year, state.month - 1 + delta, 1);
  state.year = d.getFullYear();
  state.month = d.getMonth() + 1;
  load(root);
}

async function load(root) {
  $("#month-title", root).textContent = monthTitle(state.year, state.month);
  const el = $("#budget", root);
  let data;
  try {
    data = await api(`/api/budget?year=${state.year}&month=${state.month}`);
  } catch (e) {
    el.innerHTML = `<p class="empty">Não foi possível carregar o orçamento: ${esc(e.message)}</p>`;
    return;
  }
  const withLimit = data.categories.filter((c) => c.budget_limit != null);
  const without = data.categories.filter((c) => c.budget_limit == null);
  const budgetedSpent = withLimit.reduce((s, c) => s + c.spent, 0);
  const used = data.total_budget ? budgetedSpent / data.total_budget : 0;

  el.innerHTML = `
    ${withLimit.length ? `
      <div class="story story-sm">
        <p>Das categorias com limite, você usou <strong>${brl(budgetedSpent)}</strong> de <strong>${brl(data.total_budget)}</strong>.</p>
      </div>
      <div class="pace">
        <div class="pace-track" role="img" aria-label="${pct(used)} do orçamento usado">
          <div class="pace-fill ${used > 1 ? "over" : ""}" style="width:${Math.min(used, 1) * 100}%"></div>
        </div>
        <p class="pace-caption"><b>${pct(used)}</b> do orçamento usado${used > 1 ? `, ${brl(budgetedSpent - data.total_budget)} acima do limite` : ""}.</p>
      </div>`
    : `<p class="story-note">Nenhuma categoria tem limite ainda. Defina um limite abaixo para acompanhar seus gastos ao longo do mês.</p>`}

    ${withLimit.length ? `<article class="panel"><h2>Com limite</h2><ul class="budget-list">${withLimit.map(row).join("")}</ul></article>` : ""}
    <article class="panel"><h2>Sem limite definido</h2>
      ${without.length ? `<ul class="budget-list">${without.map(row).join("")}</ul>` : `<p class="empty">Todas as categorias têm limite.</p>`}
    </article>`;

  el.querySelectorAll("button[data-id]").forEach((b) => b.addEventListener("click", async () => {
    const c = data.categories.find((x) => String(x.id) === b.dataset.id);
    const saved = await formDialog({
      title: `Limite mensal de ${c.name}`,
      fields: [{ name: "limit", label: "Limite (R$). Use 0 para remover o limite.", type: "number", step: "0.01", min: "0", required: true, value: c.budget_limit ?? "", autofocus: true }],
      submitLabel: "Salvar limite",
      onSubmit: (v) => api(`/api/categories/${c.id}/budget`, { method: "PUT", body: { limit: Number(v.limit) } }),
    });
    if (saved) { toast(`Limite de ${c.name} salvo.`); load(root); }
  }));
}

function row(c) {
  const has = c.budget_limit != null;
  const ratio = has && c.budget_limit ? c.spent / c.budget_limit : 0;
  const [label, tone] = has ? STATUS[c.status] || STATUS.ok : ["", ""];
  return `<li class="budget-row">
    <div class="budget-info">
      <p class="goal-name">${esc(c.name)}</p>
      <p class="goal-meta">${has ? `${brl(c.spent)} de ${brl(c.budget_limit)}` : `${brl(c.spent)} gastos neste mês`}</p>
    </div>
    ${has ? `<div class="budget-bar">
      <div class="goal-bar tone-${tone}"><span style="width:${Math.min(ratio, 1) * 100}%"></span></div>
      <p class="status tone-${tone}">${tone === "bad" || tone === "warn" ? icon("alert") : ""}${label} (${pct(ratio)})</p>
    </div>` : `<div class="budget-bar"></div>`}
    <button class="btn btn-sm" type="button" data-id="${c.id}">${has ? "Alterar limite" : "Definir limite"}</button>
  </li>`;
}
