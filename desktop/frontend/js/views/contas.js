// Contas: onde o dinheiro está (corrente, poupança, cartão, investimentos...).

import { api, brl, confirmDialog, esc, formDialog, icon, toast, $ } from "../core.js";

export const ACCOUNT_TYPES = [
  ["checking", "Conta corrente"], ["savings", "Poupança"], ["credit_card", "Cartão de crédito"],
  ["investment", "Investimentos"], ["cash", "Dinheiro"], ["other", "Outra"],
];
const typeName = Object.fromEntries(ACCOUNT_TYPES);

export async function render(root) {
  root.innerHTML = `
    <div class="page-head">
      <h1 class="page-title">Contas</h1>
      <button class="btn btn-primary" type="button" id="add-btn">${icon("plus")}<span>Nova conta</span></button>
    </div>
    <div id="accounts" class="stack"></div>`;
  $("#add-btn", root).addEventListener("click", () => edit(root));
  load(root);
}

async function load(root) {
  const el = $("#accounts", root);
  let accounts;
  try {
    accounts = await api("/api/accounts");
  } catch (e) {
    el.innerHTML = `<p class="empty">Não foi possível carregar as contas: ${esc(e.message)}</p>`;
    return;
  }
  if (!accounts.length) {
    el.innerHTML = `<p class="empty">Nenhuma conta cadastrada. Crie uma para separar transações por banco ou cartão.</p>`;
    return;
  }
  const total = accounts.reduce((s, a) => s + (a.balance || 0), 0);
  el.innerHTML = `
    <div class="story story-sm"><p>Somando todas as contas: <strong class="${total >= 0 ? "" : "down"}">${brl(total)}</strong>.</p></div>
    <article class="panel"><table class="table">
      <thead><tr><th>Conta</th><th>Tipo</th><th class="num">Saldo</th><th class="actions"><span class="sr-only">Ações</span></th></tr></thead>
      <tbody>${accounts.map((a) => `<tr data-id="${a.id}">
        <td><span class="goal-name">${esc(a.name)}</span>${a.notes ? `<span class="ticker-name"> ${esc(a.notes)}</span>` : ""}</td>
        <td>${esc(typeName[a.account_type] || a.account_type)}</td>
        <td class="num ${a.balance < 0 ? "down" : ""}">${brl(a.balance)}</td>
        <td class="actions">
          <button class="icon-btn" data-act="edit" aria-label="Editar ${esc(a.name)}">${icon("edit")}</button>
          <button class="icon-btn" data-act="delete" aria-label="Excluir ${esc(a.name)}">${icon("trash")}</button>
        </td></tr>`).join("")}</tbody></table>
    </article>`;

  el.querySelectorAll("button[data-act]").forEach((b) => b.addEventListener("click", async () => {
    const acc = accounts.find((a) => String(a.id) === b.closest("tr").dataset.id);
    if (b.dataset.act === "edit") return edit(root, acc);
    if (!await confirmDialog({ title: `Excluir ${acc.name}?`, message: "A conta deixa de aparecer. As transações dela continuam registradas.", confirmLabel: "Excluir conta" })) return;
    try {
      await api(`/api/accounts/${acc.id}`, { method: "DELETE" });
      toast("Conta excluída.");
      load(root);
    } catch (e) {
      toast(e.message, "error");
    }
  }));
}

async function edit(root, acc) {
  const saved = await formDialog({
    title: acc ? `Editar ${acc.name}` : "Nova conta",
    submitLabel: acc ? "Salvar alterações" : "Criar conta",
    fields: [
      { name: "name", label: "Nome", required: true, value: acc?.name, placeholder: "Ex.: Nubank", autofocus: true },
      { name: "account_type", label: "Tipo", type: "select", value: acc?.account_type || "checking", options: ACCOUNT_TYPES },
      { name: "balance", label: "Saldo atual (R$)", type: "number", step: "0.01", value: acc?.balance ?? 0 },
      { name: "notes", label: "Observações", type: "textarea", value: acc?.notes || "" },
    ],
    onSubmit: (v) => {
      const body = { ...v, balance: Number(v.balance || 0) };
      return acc ? api(`/api/accounts/${acc.id}`, { method: "PUT", body }) : api("/api/accounts", { method: "POST", body });
    },
  });
  if (saved) { toast(acc ? "Conta atualizada." : "Conta criada."); load(root); }
}
