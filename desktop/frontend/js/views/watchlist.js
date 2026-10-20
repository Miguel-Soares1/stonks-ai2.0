// Watchlist: ativos acompanhados, preço-alvo e distância até ele.

import { api, changeHtml, confirmDialog, esc, formDialog, icon, money, num, toast, $ } from "../core.js";

export async function render(root) {
  root.innerHTML = `
    <div class="page-head"><h1 class="page-title">Watchlist</h1></div>
    <form class="inline-form" id="add-form">
      <label class="field"><span>Ticker</span><input name="ticker" placeholder="Ex.: ITUB4" autocomplete="off" required></label>
      <label class="field"><span>Preço-alvo (opcional)</span><input name="target" type="number" step="0.01" min="0.01"></label>
      <button class="btn btn-primary" type="submit">${icon("plus")}<span>Adicionar</span></button>
    </form>
    <article class="panel"><div id="list"><p class="empty">Buscando cotações…</p></div></article>`;

  $("#add-form", root).addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const values = new FormData(form);
    try {
      const item = await api("/api/watchlist", { method: "POST", body: {
        ticker: values.get("ticker").trim(),
        target_price: values.get("target") ? Number(values.get("target")) : null,
      } });
      toast(`${item.ticker} adicionado à watchlist.`);
      form.reset();
      load(root);
    } catch (err) {
      toast(err.message, "error");
    }
  });
  load(root);
}

async function load(root) {
  const el = $("#list", root);
  let rows;
  try {
    rows = await api("/api/watchlist");
  } catch (e) {
    el.innerHTML = `<p class="empty">Não foi possível carregar a watchlist: ${esc(e.message)}</p>`;
    return;
  }
  if (!rows.length) {
    el.innerHTML = `<p class="empty">Nenhum ativo ainda. Adicione um ticker acima para acompanhar o preço.</p>`;
    return;
  }
  el.innerHTML = `<table class="table">
    <thead><tr><th>Ativo</th><th class="num">Preço</th><th class="num">Variação no dia</th>
      <th class="num">Preço-alvo</th><th class="num">Até o alvo</th><th class="actions"><span class="sr-only">Ações</span></th></tr></thead>
    <tbody>${rows.map((r) => {
      const gap = r.target_price && r.price ? ((r.target_price - r.price) / r.price) * 100 : null;
      return `<tr data-id="${r.id}">
        <td><a class="ticker" href="#ativos/${encodeURIComponent(r.ticker)}">${esc(r.ticker)}</a> <span class="ticker-name">${esc(r.name || r.exchange)}</span></td>
        <td class="num">${r.price == null ? `<span class="muted">${esc(r.error || "—")}</span>` : money(r.price, r.currency)}</td>
        <td class="num">${changeHtml(r.change_percent)}</td>
        <td class="num">${r.target_price ? money(r.target_price, r.currency) : "—"}</td>
        <td class="num">${gap == null ? "—" : `${gap >= 0 ? "+" : "−"}${num(Math.abs(gap), 1)}%`}</td>
        <td class="actions">
          <button class="icon-btn" data-act="target" aria-label="Definir preço-alvo de ${esc(r.ticker)}">${icon("edit")}</button>
          <button class="icon-btn" data-act="remove" aria-label="Remover ${esc(r.ticker)}">${icon("trash")}</button>
        </td>
      </tr>`;
    }).join("")}</tbody></table>`;

  el.querySelectorAll("button[data-act]").forEach((b) => b.addEventListener("click", async () => {
    const id = b.closest("tr").dataset.id;
    const row = rows.find((r) => String(r.id) === id);
    if (b.dataset.act === "remove") {
      if (!await confirmDialog({ title: `Remover ${row.ticker}?`, message: "O ativo sai da watchlist. Você pode adicioná-lo de novo depois.", confirmLabel: "Remover" })) return;
      await api(`/api/watchlist/${id}`, { method: "DELETE" });
      toast(`${row.ticker} removido da watchlist.`);
      load(root);
    } else {
      const saved = await formDialog({
        title: `Preço-alvo de ${row.ticker}`,
        fields: [{ name: "target", label: "Preço-alvo (deixe vazio para remover)", type: "number", step: "0.01", min: "0.01", value: row.target_price ?? "", autofocus: true }],
        submitLabel: "Salvar preço-alvo",
        onSubmit: (v) => api(`/api/watchlist/${id}`, { method: "PATCH", body: { target_price: v.target ? Number(v.target) : null } }),
      });
      if (saved) { toast("Preço-alvo salvo."); load(root); }
    }
  }));
}
