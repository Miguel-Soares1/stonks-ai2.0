// Metas: objetivos com valor-alvo, prazo e contribuições.

import { api, brl, confirmDialog, esc, formDialog, icon, isoDate, toast, $ } from "../core.js";
import { goalItem } from "./inicio.js";

const TYPES = [
  ["savings", "Guardar dinheiro"], ["emergency", "Reserva de emergência"], ["purchase", "Compra"],
  ["investment", "Investir"], ["debt", "Quitar dívida"], ["custom", "Outro"],
];
const PRIORITIES = [["low", "Baixa"], ["medium", "Média"], ["high", "Alta"]];
const STATUSES = [["active", "Ativa"], ["paused", "Pausada"], ["completed", "Concluída"], ["cancelled", "Cancelada"]];
const label = (list, v) => (list.find(([k]) => k === v) || [, v])[1];

let status = "active";

export async function render(root) {
  root.innerHTML = `
    <div class="page-head">
      <h1 class="page-title">Metas</h1>
      <button class="btn btn-primary" type="button" id="add-btn">${icon("plus")}<span>Nova meta</span></button>
    </div>
    <div class="filters">
      <div class="seg" role="radiogroup" aria-label="Mostrar">
        ${[["active", "Ativas"], ["completed", "Concluídas"], ["all", "Todas"]].map(([v, l]) =>
          `<label><input type="radio" name="status" value="${v}" ${v === status ? "checked" : ""}><span>${l}</span></label>`).join("")}
      </div>
    </div>
    <div id="goals" class="stack"></div>`;
  root.querySelectorAll("input[name=status]").forEach((r) => r.addEventListener("change", () => { status = r.value; load(root); }));
  $("#add-btn", root).addEventListener("click", () => edit(root));
  load(root);
}

async function load(root) {
  const el = $("#goals", root);
  let goals;
  try {
    goals = await api(`/api/goals?status=${status}`);
  } catch (e) {
    el.innerHTML = `<p class="empty">Não foi possível carregar as metas: ${esc(e.message)}</p>`;
    return;
  }
  if (!goals.length) {
    el.innerHTML = `<p class="empty">${status === "active" ? "Nenhuma meta ativa. Crie uma para acompanhar quanto falta e quanto guardar por mês." : "Nenhuma meta aqui."}</p>`;
    return;
  }
  el.innerHTML = `<div class="grid grid-2">${goals.map((g) => `
    <article class="panel goal-card" data-id="${g.id}">
      ${goalItem(g)}
      <p class="goal-meta">${esc(label(TYPES, g.goal_type))}, prioridade ${esc(label(PRIORITIES, g.priority).toLowerCase())}${g.status !== "active" ? `, ${esc(label(STATUSES, g.status).toLowerCase())}` : ""}.
        ${g.monthly_contribution ? `Sugestão: guardar ${brl(g.monthly_contribution)} por mês.` : ""}</p>
      ${g.description ? `<p class="small">${esc(g.description)}</p>` : ""}
      <div class="card-actions">
        ${g.status === "active" ? `<button class="btn btn-sm btn-primary" data-act="contribute">${icon("plus")}<span>Adicionar valor</span></button>` : ""}
        <button class="btn btn-sm" data-act="edit">Editar</button>
        <button class="icon-btn" data-act="delete" aria-label="Excluir ${esc(g.name)}">${icon("trash")}</button>
      </div>
    </article>`).join("")}</div>`;

  el.querySelectorAll("button[data-act]").forEach((b) => b.addEventListener("click", async () => {
    const g = goals.find((x) => String(x.id) === b.closest("[data-id]").dataset.id);
    if (b.dataset.act === "edit") return edit(root, g);
    if (b.dataset.act === "delete") {
      if (!await confirmDialog({ title: `Excluir "${g.name}"?`, message: "A meta e o progresso registrado serão apagados.", confirmLabel: "Excluir meta" })) return;
      await api(`/api/goals/${g.id}`, { method: "DELETE" });
      toast("Meta excluída.");
      return load(root);
    }
    const updated = await formDialog({
      title: `Adicionar a "${g.name}"`,
      fields: [{ name: "amount", label: `Valor (faltam ${brl(g.remaining_amount)})`, type: "number", step: "0.01", min: "0.01", required: true, autofocus: true }],
      submitLabel: "Adicionar valor",
      onSubmit: (v) => api(`/api/goals/${g.id}/contribute`, { method: "POST", body: { amount: Number(v.amount) } }),
    });
    if (updated) {
      toast(updated.status === "completed" ? `Meta "${g.name}" concluída!` : "Valor adicionado.");
      load(root);
    }
  }));
}

async function edit(root, g) {
  const saved = await formDialog({
    title: g ? `Editar "${g.name}"` : "Nova meta",
    submitLabel: g ? "Salvar alterações" : "Criar meta",
    fields: [
      { name: "name", label: "Nome", required: true, value: g?.name, placeholder: "Ex.: Reserva de emergência", autofocus: true },
      { name: "target_amount", label: "Valor-alvo (R$)", type: "number", step: "0.01", min: "0.01", required: true, value: g?.target_amount },
      { name: "deadline", label: "Prazo (opcional)", type: "date", value: isoDate(g?.deadline) },
      { name: "goal_type", label: "Tipo", type: "select", value: g?.goal_type || "savings", options: TYPES },
      { name: "priority", label: "Prioridade", type: "select", value: g?.priority || "medium", options: PRIORITIES },
      ...(g ? [{ name: "status", label: "Situação", type: "select", value: g.status, options: STATUSES }] : []),
      { name: "description", label: "Descrição (opcional)", type: "textarea", value: g?.description || "" },
    ],
    onSubmit: (v) => {
      const body = { ...v, target_amount: Number(v.target_amount) };
      return g ? api(`/api/goals/${g.id}`, { method: "PUT", body }) : api("/api/goals", { method: "POST", body });
    },
  });
  if (saved) { toast(g ? "Meta atualizada." : "Meta criada."); load(root); }
}
