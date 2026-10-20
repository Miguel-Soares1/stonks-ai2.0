// Início: o mês contado em uma frase, ritmo de gastos, gráficos, metas e watchlist.

import { aiPanel, api, brl, changeHtml, esc, icon, money, monthName, monthTitle, moneyCompact, pct, shortDate, $ } from "../core.js";
import { groupedBars, lineChart } from "../charts.js";

const today = new Date();
const state = { year: today.getFullYear(), month: today.getMonth() + 1 };

export async function render(root) {
  root.innerHTML = `
    <div class="month-nav">
      <h1 class="month-title" id="month-title"></h1>
      <div class="month-buttons">
        <button class="icon-btn" id="month-prev" type="button" aria-label="Mês anterior">${icon("left")}</button>
        <button class="icon-btn" id="month-next" type="button" aria-label="Próximo mês">${icon("right")}</button>
      </div>
    </div>
    <div class="story" id="story" aria-live="polite"></div>
    <div class="pace" id="pace"></div>
    <div id="month-ai"></div>
    <div id="alerts"></div>
    <div class="grid">
      <article class="panel panel-wide"><h2>Saldo acumulado em 90 dias</h2><div class="chart" id="balance-chart"></div></article>
      <article class="panel"><h2>Para onde foi o dinheiro</h2><div id="categories"></div></article>
      <article class="panel panel-wide"><h2>Receitas e despesas nos últimos 6 meses</h2><div class="chart chart-bars" id="months-chart"></div></article>
      <article class="panel"><h2>Metas</h2><div id="goals"></div></article>
      <article class="panel panel-full" id="upcoming-panel" hidden><div class="panel-head"><h2>Recorrentes no próximo mês</h2><a class="link" href="#transacoes">Ver transações</a></div><div id="upcoming"></div></article>
      <article class="panel panel-full"><div class="panel-head"><h2>Watchlist</h2><a class="link" href="#watchlist">Gerenciar</a></div><div id="watchlist"></div></article>
    </div>`;

  $("#month-prev", root).addEventListener("click", () => shiftMonth(root, -1));
  $("#month-next", root).addEventListener("click", () => shiftMonth(root, 1));
  loadMonth(root);
  loadMonths(root);
  loadWatchlist(root);
}

function shiftMonth(root, delta) {
  const d = new Date(state.year, state.month - 1 + delta, 1);
  state.year = d.getFullYear();
  state.month = d.getMonth() + 1;
  loadMonth(root);
}

async function loadMonth(root) {
  const isCurrent = state.year === today.getFullYear() && state.month === today.getMonth() + 1;
  $("#month-title", root).textContent = monthTitle(state.year, state.month);
  $("#month-next", root).disabled = isCurrent;
  try {
    const d = await api(`/api/dashboard?year=${state.year}&month=${state.month}`);
    renderStory(root, d, isCurrent);
    renderPace(root, d, isCurrent);
    renderAlerts(root, d.alerts);
    lineChart($("#balance-chart", root), [{ name: "Saldo", color: "var(--brand)", points:
      d.balance_history.every((p) => p.balance === 0) ? [] : d.balance_history.map((p) => ({ date: p.date, value: p.balance })) }],
      { yFormat: (v) => moneyCompact(v), tooltipFormat: brl, area: true, baseline: 0,
        label: "Saldo acumulado nos últimos 90 dias", emptyMessage: "Sem movimentações nos últimos 90 dias." });
    renderCategories(root, d.summary.top_categories);
    renderGoals(root, d.goals);
    renderUpcoming(root, d.upcoming_recurring);
    const monthAi = $("#month-ai", root);
    if (d.summary.transaction_count) {
      aiPanel(monthAi, { label: "Resumir o mês com IA",
        path: `/api/dashboard/summary-ai?year=${state.year}&month=${state.month}` });
    } else {
      monthAi.innerHTML = "";
    }
  } catch (e) {
    $("#story", root).innerHTML = `<p class="story-note">Não foi possível carregar os dados do mês: ${esc(e.message)}</p>`;
    $("#pace", root).innerHTML = "";
  }
}

function renderStory(root, d, isCurrent) {
  const s = d.summary;
  const name = monthName(d.period.year, d.period.month);
  if (!s.transaction_count) {
    $("#story", root).innerHTML = `
      <p>Nenhuma transação em ${esc(name)}.</p>
      <p class="story-note">Arraste um extrato (CSV, Excel ou PDF) para esta janela,
      ou <a class="link" href="#transacoes">adicione uma transação</a>.</p>`;
    return;
  }
  const sign = s.balance >= 0;
  const rest = isCurrent ? (sign ? "Até agora, sobram" : "Até agora, faltam") : (sign ? "Sobraram" : "Faltaram");
  let note = "";
  const p = d.previous;
  if (p && p.transaction_count) {
    const prevName = monthName(p.year, p.month);
    const diff = s.total_expense - p.total_expense;
    const scope = isCurrent ? `em todo o mês de ${prevName}` : `em ${prevName}`;
    if (Math.abs(diff) >= 0.01) {
      note = `<p class="story-note">Você gastou ${brl(Math.abs(diff))} ${diff > 0 ? "a mais" : "a menos"} que ${scope}.</p>`;
    }
  }
  $("#story", root).innerHTML = `
    <p>Em ${esc(name)}, entraram <strong>${brl(s.total_income)}</strong>
    e saíram <strong>${brl(s.total_expense)}</strong>.
    ${rest} <strong class="${sign ? "up" : "down"}">${sign ? "▲" : "▼"}&nbsp;${brl(Math.abs(s.balance))}</strong>.</p>
    ${note}`;
}

function renderPace(root, d, isCurrent) {
  const s = d.summary;
  const el = $("#pace", root);
  if (!s.transaction_count) { el.innerHTML = ""; return; }
  if (s.total_income <= 0) {
    el.innerHTML = `<p class="pace-caption">Não há receitas neste mês, então não dá para comparar o ritmo dos gastos.</p>`;
    return;
  }
  const spent = s.total_expense / s.total_income;
  const time = d.period.day / d.period.days_in_month;
  const caption = isCurrent
    ? `Já saiu <b>${pct(spent)}</b> do que entrou, e passaram <b>${pct(time)}</b> dos dias do mês.`
    : `Saiu <b>${pct(spent)}</b> do que entrou neste mês.`;
  el.innerHTML = `
    <div class="pace-track" role="img" aria-label="Gasto ${pct(spent)} da renda${isCurrent ? `, ${pct(time)} do mês passou` : ""}">
      <div class="pace-fill ${spent > 1 ? "over" : ""}" style="width:0"></div>
      ${isCurrent ? `<div class="pace-marker" style="left:${(time * 100).toFixed(2)}%" title="Hoje"></div>` : ""}
    </div>
    <p class="pace-caption">${caption}</p>`;
  requestAnimationFrame(() => { $(".pace-fill", el).style.width = `${Math.min(spent, 1) * 100}%`; });
}

function renderAlerts(root, alerts) {
  const el = $("#alerts", root);
  if (!alerts || !alerts.length) { el.innerHTML = ""; return; }
  el.innerHTML = `<ul class="alert-list">${alerts.slice(0, 3).map((a) => `
    <li class="alert ${a.severity === "high" ? "critical" : ""}">
      ${icon("alert")}
      <div><p class="alert-title">${esc(a.title)}</p><p>${esc(a.message)}</p></div>
    </li>`).join("")}</ul>
    ${alerts.length > 3 ? `<p class="small"><a class="link" href="#alertas">Ver todos os ${alerts.length} alertas</a></p>` : ""}`;
}

function renderCategories(root, cats) {
  const el = $("#categories", root);
  if (!cats || !cats.length) { el.innerHTML = `<p class="empty">Nenhuma despesa neste mês.</p>`; return; }
  const max = Math.max(...cats.map((c) => c.amount));
  el.innerHTML = `<ul class="cat-list">${cats.slice(0, 6).map((c) => `
    <li class="cat-row">
      <span class="cat-name">${esc(c.name)}</span>
      <span class="cat-value">${brl(c.amount)} (${c.percent.toLocaleString("pt-BR")}%)</span>
      <div class="cat-bar"><span style="width:${(c.amount / max) * 100}%"></span></div>
    </li>`).join("")}</ul>`;
}

export function goalItem(g) {
  const p = Math.max(0, Math.min(100, g.progress_percent || 0));
  const when = g.days_remaining == null ? "Sem prazo"
    : g.days_remaining < 0 ? "Prazo vencido" : `Faltam ${g.days_remaining} dias`;
  const track = g.status === "active" && g.is_on_track === false ? ", abaixo do ritmo necessário" : "";
  return `
    <div class="goal-head"><span class="goal-name">${esc(g.name)}</span><span>${Math.round(p)}%</span></div>
    <div class="goal-bar" role="img" aria-label="${Math.round(p)}% concluído"><span style="width:${p}%"></span></div>
    <p class="goal-meta">${brl(g.current_amount)} de ${brl(g.target_amount)}. ${when}${track}.</p>`;
}

function renderGoals(root, goals) {
  const el = $("#goals", root);
  if (!goals || !goals.length) {
    el.innerHTML = `<p class="empty">Nenhuma meta ativa. <a class="link" href="#metas">Criar uma meta</a></p>`;
    return;
  }
  el.innerHTML = `<ul class="goal-list">${goals.slice(0, 4).map((g) => `<li>${goalItem(g)}</li>`).join("")}</ul>`;
}

// Contas fixas e receitas que se repetem: o que ainda vai entrar e sair
function renderUpcoming(root, items) {
  const panel = $("#upcoming-panel", root);
  panel.hidden = !items || !items.length;
  if (panel.hidden) return;
  const out = items.filter((i) => i.type === "expense").reduce((s, i) => s + i.amount, 0);
  const inc = items.filter((i) => i.type === "income").reduce((s, i) => s + i.amount, 0);
  $("#upcoming", root).innerHTML = `
    <p class="muted small">Previsto: ${inc ? `entram <strong>${brl(inc)}</strong> e ` : ""}saem <strong>${brl(out)}</strong>.</p>
    <ul class="upcoming-list">${items.slice(0, 8).map((i) => `
      <li>
        <span class="upcoming-date">${shortDate(i.date)}</span>
        <span>${esc(i.description)}<span class="upcoming-meta">${esc(i.category_name)} · ${esc(i.frequency_label)}</span></span>
        <span class="num ${i.type === "income" ? "amount-in" : ""}">${i.type === "income" ? "+" : "−"}${brl(i.amount)}</span>
      </li>`).join("")}</ul>`;
}

async function loadMonths(root) {
  const el = $("#months-chart", root);
  try {
    const months = await api("/api/months?count=6");
    if (months.every((m) => !m.transaction_count)) {
      el.innerHTML = `<p class="empty">Sem transações nos últimos 6 meses.</p>`;
      return;
    }
    groupedBars(el, months.map((m) => ({
      label: new Intl.DateTimeFormat("pt-BR", { month: "short" }).format(new Date(m.year, m.month - 1, 1)).replace(".", ""),
      values: [m.total_income, m.total_expense],
    })), [{ name: "Receitas", color: "var(--series-1)" }, { name: "Despesas", color: "var(--series-2)" }],
    { yFormat: (v) => moneyCompact(v), tooltipFormat: brl, label: "Receitas e despesas por mês" });
  } catch (e) {
    el.innerHTML = `<p class="empty">${esc(e.message)}</p>`;
  }
}

async function loadWatchlist(root) {
  const el = $("#watchlist", root);
  el.innerHTML = `<p class="empty">Buscando cotações…</p>`;
  try {
    const rows = await api("/api/watchlist");
    if (!rows.length) {
      el.innerHTML = `<p class="empty">Nenhum ativo na watchlist. Use Ctrl K para abrir um ativo e adicioná-lo.</p>`;
      return;
    }
    el.innerHTML = `<table class="table">
      <thead><tr><th>Ativo</th><th class="num">Preço</th><th class="num">Variação no dia</th><th class="num">Preço-alvo</th></tr></thead>
      <tbody>${rows.slice(0, 6).map((r) => `<tr>
        <td><a class="ticker" href="#ativos/${encodeURIComponent(r.ticker)}">${esc(r.ticker)}</a> <span class="ticker-name">${esc(r.name || r.exchange)}</span></td>
        <td class="num">${r.price == null ? `<span class="muted">${esc(r.error || "—")}</span>` : money(r.price, r.currency)}</td>
        <td class="num">${changeHtml(r.change_percent)}</td>
        <td class="num">${r.target_price ? money(r.target_price, r.currency) : "—"}</td>
      </tr>`).join("")}</tbody></table>`;
  } catch (e) {
    el.innerHTML = `<p class="empty">Não foi possível carregar a watchlist: ${esc(e.message)}</p>`;
  }
}
