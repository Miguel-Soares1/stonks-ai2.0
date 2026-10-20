// Transações: lista com filtros, adicionar/editar/excluir e importação de extrato.

import { api, brl, confirmDialog, esc, formDialog, fullDate, icon, isoDate, toast, todayIso, $ } from "../core.js";

const PAGE = 50;
const filters = { days: "30", type: "", account_id: "" };
let lookups = { categories: [], accounts: [] };

export async function render(root) {
  root.innerHTML = `
    <div class="page-head">
      <h1 class="page-title">Transações</h1>
      <div class="toolbar">
        <label class="btn" for="import-input">${icon("upload")}<span>Importar extrato</span></label>
        <input id="import-input" type="file" accept=".csv,.xlsx,.xls,.pdf" hidden>
        <button class="btn btn-primary" type="button" id="add-btn">${icon("plus")}<span>Nova transação</span></button>
      </div>
    </div>
    <p class="muted small">Você também pode arrastar um extrato (CSV, Excel ou PDF) para qualquer lugar da janela.</p>
    <div class="filters">
      <label class="field"><span>Período</span>
        <select name="days">${[["7", "7 dias"], ["30", "30 dias"], ["90", "90 dias"], ["365", "12 meses"], ["0", "Tudo"]]
          .map(([v, l]) => `<option value="${v}" ${v === filters.days ? "selected" : ""}>${l}</option>`).join("")}</select></label>
      <div class="field" role="radiogroup" aria-labelledby="type-label"><span id="type-label">Tipo</span><div class="seg">
        ${[["", "Todas"], ["expense", "Despesas"], ["income", "Receitas"]].map(([v, l]) =>
          `<label><input type="radio" name="type" value="${v}" ${v === filters.type ? "checked" : ""}><span>${l}</span></label>`).join("")}
      </div></div>
      <label class="field"><span>Conta</span><select name="account_id"><option value="">Todas</option></select></label>
    </div>
    <article class="panel"><div id="tx-list"><p class="empty">Carregando…</p></div></article>`;

  [lookups.categories, lookups.accounts] = await Promise.all([
    api("/api/categories").catch(() => []), api("/api/accounts").catch(() => []),
  ]);
  const accSel = $("select[name=account_id]", root);
  accSel.insertAdjacentHTML("beforeend", lookups.accounts.map((a) =>
    `<option value="${a.id}" ${String(a.id) === filters.account_id ? "selected" : ""}>${esc(a.name)}</option>`).join(""));

  root.querySelectorAll(".filters select, .filters input").forEach((el) => el.addEventListener("change", () => {
    filters[el.name] = el.value;
    load(root, true);
  }));
  $("#add-btn", root).addEventListener("click", () => editTransaction(root));
  $("#import-input", root).addEventListener("change", async (e) => {
    const file = e.target.files[0];
    e.target.value = "";
    if (file) { await importFile(file); load(root, true); }
  });
  load(root, true);
}

let loaded = [];

async function load(root, reset) {
  const el = $("#tx-list", root);
  if (reset) loaded = [];
  const qs = new URLSearchParams({ days: filters.days, limit: PAGE, offset: loaded.length });
  if (filters.type) qs.set("type", filters.type);
  if (filters.account_id) qs.set("account_id", filters.account_id);
  let page;
  try {
    page = await api(`/api/transactions?${qs}`);
  } catch (e) {
    el.innerHTML = `<p class="empty">Não foi possível carregar as transações: ${esc(e.message)}</p>`;
    return;
  }
  loaded = loaded.concat(page);
  if (!loaded.length) {
    el.innerHTML = `<p class="empty">Nenhuma transação neste filtro. Importe um extrato ou adicione uma transação.</p>`;
    return;
  }
  const accName = Object.fromEntries(lookups.accounts.map((a) => [a.id, a.name]));
  el.innerHTML = `<table class="table">
    <thead><tr><th>Data</th><th>Descrição</th><th>Categoria</th><th class="num">Valor</th><th class="actions"><span class="sr-only">Ações</span></th></tr></thead>
    <tbody>${loaded.map((t) => `<tr data-id="${t.id}">
      <td class="nowrap">${fullDate(t.date)}</td>
      <td>${esc(t.description)}${t.account_id && accName[t.account_id] ? `<span class="ticker-name"> ${esc(accName[t.account_id])}</span>` : ""}</td>
      <td>${esc(t.category_name || "Sem categoria")}</td>
      <td class="num ${t.type === "income" ? "amount-in" : ""}">${t.type === "income" ? "+" : "−"}${brl(t.amount)}</td>
      <td class="actions">
        <button class="icon-btn" data-act="edit" aria-label="Editar">${icon("edit")}</button>
        <button class="icon-btn" data-act="delete" aria-label="Excluir">${icon("trash")}</button>
      </td></tr>`).join("")}</tbody></table>
    ${page.length === PAGE ? `<div class="more"><button class="btn" type="button" id="more-btn">Mostrar mais</button></div>` : ""}`;

  el.querySelectorAll("button[data-act]").forEach((b) => b.addEventListener("click", async () => {
    const tx = loaded.find((t) => String(t.id) === b.closest("tr").dataset.id);
    if (b.dataset.act === "edit") return editTransaction(root, tx);
    if (!await confirmDialog({ title: "Excluir transação?", message: `"${tx.description}" de ${brl(tx.amount)} será apagada.`, confirmLabel: "Excluir" })) return;
    try {
      await api(`/api/transactions/${tx.id}`, { method: "DELETE" });
      toast("Transação excluída.");
      load(root, true);
    } catch (e) {
      toast(e.message, "error");
    }
  }));
  const more = $("#more-btn", el);
  if (more) more.addEventListener("click", () => load(root, false));
}

async function editTransaction(root, tx) {
  const editing = Boolean(tx);
  const saved = await formDialog({
    title: editing ? "Editar transação" : "Nova transação",
    submitLabel: editing ? "Salvar alterações" : "Adicionar transação",
    fields: [
      { name: "type", label: "Tipo", type: "segmented", value: tx?.type || "expense", options: [["expense", "Despesa"], ["income", "Receita"]] },
      { name: "description", label: "Descrição", required: true, value: tx?.description, autofocus: true },
      { name: "amount", label: "Valor (R$)", type: "number", step: "0.01", min: "0.01", required: true, value: tx?.amount },
      { name: "date", label: "Data", type: "date", required: true, value: isoDate(tx?.date) || todayIso() },
      { name: "category_name", label: "Categoria", type: "select", value: tx?.category_name || "",
        options: [["", editing ? "Sem categoria" : "Detectar automaticamente"], ...lookups.categories.map((c) => [c.name, c.name])] },
      ...(editing ? [] : [{ name: "account_id", label: "Conta", type: "select", value: "",
        options: [["", "Nenhuma"], ...lookups.accounts.map((a) => [a.id, a.name])] }]),
      { name: "notes", label: "Observações", type: "textarea", value: tx?.notes || "" },
    ],
    onSubmit: (v) => {
      const body = { ...v, amount: Number(v.amount), account_id: v.account_id ? Number(v.account_id) : null };
      return editing
        ? api(`/api/transactions/${tx.id}`, { method: "PUT", body })
        : api("/api/transactions", { method: "POST", body });
    },
  });
  if (saved) {
    toast(editing ? "Transação atualizada." : "Transação adicionada.");
    load(root, true);
  }
}

// Usada aqui e pelo arrastar-e-soltar global (main.js)
export async function importFile(file) {
  toast(`Importando ${file.name}…`);
  try {
    const r = await api(`/api/import?filename=${encodeURIComponent(file.name)}`, { method: "POST", raw: file });
    const parts = [`${r.imported} ${r.imported === 1 ? "transação importada" : "transações importadas"}`];
    if (r.duplicates) parts.push(`${r.duplicates} ${r.duplicates === 1 ? "repetida ignorada" : "repetidas ignoradas"}`);
    if (r.errors.length) {
      toast(`${parts.join(", ")}. Problemas: ${r.errors.slice(0, 2).join("; ")}`, "error");
    } else if (!r.imported && !r.duplicates) {
      toast("Nenhuma transação encontrada no arquivo. Verifique se é um extrato com data, descrição e valor.", "error");
    } else {
      toast(`${parts.join(", ")}.`);
    }
    return r;
  } catch (e) {
    toast(`Não foi possível importar: ${e.message}`, "error");
    return null;
  }
}
