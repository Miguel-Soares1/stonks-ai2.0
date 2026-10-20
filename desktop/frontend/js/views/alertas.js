// Alertas: avisos gerados a partir dos gastos (orçamento, metas, gastos fora do padrão).

import { api, esc, fullDate, icon, toast, $ } from "../core.js";

const SEVERITY = { high: ["Importante", "bad"], medium: ["Atenção", "warn"], low: ["Informativo", "ok"] };
let showDismissed = false;

export async function render(root) {
  root.innerHTML = `
    <div class="page-head">
      <h1 class="page-title">Alertas</h1>
      <button class="btn" type="button" id="check-btn">Verificar agora</button>
    </div>
    <div class="filters">
      <label class="check"><input type="checkbox" id="show-dismissed" ${showDismissed ? "checked" : ""}> Mostrar alertas dispensados</label>
    </div>
    <div id="alerts"></div>`;
  $("#show-dismissed", root).addEventListener("change", (e) => { showDismissed = e.target.checked; load(root); });
  $("#check-btn", root).addEventListener("click", async (e) => {
    e.target.disabled = true;
    try {
      const { created } = await api("/api/alerts/check", { method: "POST" });
      toast(created ? `${created} ${created === 1 ? "novo alerta" : "novos alertas"}.` : "Nenhum alerta novo.");
      load(root);
    } catch (err) {
      toast(err.message, "error");
    } finally {
      e.target.disabled = false;
    }
  });
  load(root);
}

async function load(root) {
  const el = $("#alerts", root);
  let alerts;
  try {
    alerts = await api(`/api/alerts?include_dismissed=${showDismissed}`);
  } catch (e) {
    el.innerHTML = `<p class="empty">Não foi possível carregar os alertas: ${esc(e.message)}</p>`;
    return;
  }
  if (!alerts.length) {
    el.innerHTML = `<p class="empty">Nenhum alerta pendente. O app avisa aqui quando um gasto passa do orçamento ou uma meta sai do ritmo.</p>`;
    return;
  }
  el.innerHTML = `<ul class="alert-list wide">${alerts.map((a) => {
    const [sevLabel, tone] = SEVERITY[a.severity] || SEVERITY.low;
    return `<li class="alert tone-${tone} ${a.dismissed ? "dismissed" : ""}" data-id="${a.id}">
      ${icon("alert")}
      <div class="grow">
        <p class="alert-title">${esc(a.title)}</p>
        <p>${esc(a.message)}</p>
        <p class="goal-meta">${sevLabel}${a.created_at ? `, ${fullDate(a.created_at)}` : ""}${a.dismissed ? ", dispensado" : ""}</p>
      </div>
      ${a.dismissed ? "" : `<button class="btn btn-sm" data-dismiss>Dispensar</button>`}
    </li>`;
  }).join("")}</ul>`;
  el.querySelectorAll("[data-dismiss]").forEach((b) => b.addEventListener("click", async () => {
    await api(`/api/alerts/${b.closest("[data-id]").dataset.id}/dismiss`, { method: "POST" });
    toast("Alerta dispensado.");
    load(root);
  }));
}
