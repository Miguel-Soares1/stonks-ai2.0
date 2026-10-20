// Ativos: cotação, histórico, fundamentos e análise da IA numa única página por ticker.

import { aiPanel, api, changeHtml, compactNum, esc, icon, money, moneyCompact, num, toast, $ } from "../core.js";
import { lineChart } from "../charts.js";

const PERIODS = [["1mo", "1M"], ["3mo", "3M"], ["6mo", "6M"], ["1y", "1A"], ["2y", "2A"], ["5y", "5A"]];

// Explicações curtas exibidas ao passar o mouse sobre cada indicador
const HINTS = {
  pe: "Preço/Lucro: quantos anos de lucro atual pagariam o preço da ação. Negativo indica prejuízo.",
  pb: "Preço/Valor patrimonial: quanto o mercado paga por cada real de patrimônio da empresa.",
  dy: "Dividend yield: proventos pagos nos últimos 12 meses em relação ao preço.",
  roe: "Retorno sobre o patrimônio: lucro gerado com o capital dos acionistas.",
  margin: "Margem líquida: quanto da receita vira lucro.",
  beta: "Beta: volatilidade em relação ao mercado. Acima de 1 oscila mais que o índice.",
};

// DY, ROE e margem chegam como fração (0,061 = 6,1%)
const pctOrDash = (v) => (v == null ? "—" : `${num(v * 100, 1)}%`);
// Fora do pregão a fonte devolve 0; zero não é um preço real
const priceOrDash = (v, currency) => (v ? money(v, currency) : "—");

export async function render(root, params) {
  const ticker = (params[0] || "").toUpperCase();
  if (!ticker) return renderPicker(root);

  root.innerHTML = `<p class="muted">Buscando ${esc(ticker)}…</p>`;
  let data;
  try {
    data = await api(`/api/asset/${encodeURIComponent(ticker)}?period=6mo`);
  } catch (e) {
    root.innerHTML = `
      <h1 class="page-title">${esc(ticker)}</h1>
      <p class="empty">Não foi possível encontrar ${esc(ticker)}: ${esc(e.message)}</p>
      <p><a class="link" href="#ativos">Buscar outro ativo</a></p>`;
    return;
  }
  const q = data.quote;
  const f = data.fundamentals;

  root.innerHTML = `
    <header class="asset-head">
      <div>
        <h1 class="page-title">${esc(q.ticker)}</h1>
        <p class="muted">${esc(q.name || "")} ${q.name ? "na" : ""} ${esc(q.exchange)}</p>
      </div>
      <div class="asset-price">
        <p class="price">${money(q.price, q.currency)}</p>
        <p>${changeHtml(q.change_percent)} <span class="muted small">hoje</span></p>
      </div>
    </header>
    <div class="toolbar">
      <button class="btn" type="button" id="watch-btn"></button>
      <a class="btn" href="#comparar/${encodeURIComponent(q.ticker)}">${icon("scale")}<span>Comparar com outros</span></a>
    </div>

    <article class="panel">
      <div class="panel-head">
        <h2>Preço de fechamento</h2>
        <div class="seg" role="radiogroup" aria-label="Período">
          ${PERIODS.map(([v, l]) => `<label><input type="radio" name="period" value="${v}" ${v === data.period ? "checked" : ""}><span>${l}</span></label>`).join("")}
        </div>
      </div>
      <p class="muted small" id="period-change"></p>
      <div class="chart" id="price-chart"></div>
    </article>

    <div class="grid grid-2">
      <article class="panel">
        <h2>Hoje</h2>
        <dl class="stats">
          <div><dt>Abertura</dt><dd>${priceOrDash(q.open_price, q.currency)}</dd></div>
          <div><dt>Fechamento anterior</dt><dd>${priceOrDash(q.previous_close, q.currency)}</dd></div>
          <div><dt>Máxima</dt><dd>${priceOrDash(q.high, q.currency)}</dd></div>
          <div><dt>Mínima</dt><dd>${priceOrDash(q.low, q.currency)}</dd></div>
          <div><dt>Volume</dt><dd>${q.volume ? compactNum(q.volume) : "—"}</dd></div>
        </dl>
        ${!q.open_price && !q.volume ? `<p class="muted small">Sem negociação registrada hoje ainda (pregão fechado ou dados atrasados).</p>` : ""}
      </article>
      <article class="panel">
        <h2>Fundamentos</h2>
        ${f ? `<dl class="stats">
          <div><dt>Setor</dt><dd>${esc(f.sector || "—")}</dd></div>
          <div><dt>Valor de mercado</dt><dd>${f.market_cap ? moneyCompact(f.market_cap, f.currency || q.currency) : "—"}</dd></div>
          <div title="${HINTS.pe}"><dt>P/L</dt><dd>${f.pe_ratio != null ? num(f.pe_ratio) : "—"}</dd></div>
          <div title="${HINTS.pb}"><dt>P/VP</dt><dd>${f.pb_ratio != null ? num(f.pb_ratio) : "—"}</dd></div>
          <div title="${HINTS.dy}"><dt>Dividend yield</dt><dd>${pctOrDash(f.dividend_yield)}</dd></div>
          <div title="${HINTS.roe}"><dt>ROE</dt><dd>${pctOrDash(f.roe)}</dd></div>
          <div title="${HINTS.margin}"><dt>Margem líquida</dt><dd>${pctOrDash(f.net_margin)}</dd></div>
          <div title="${HINTS.beta}"><dt>Beta</dt><dd>${f.beta != null ? num(f.beta) : "—"}</dd></div>
        </dl>
        <p class="muted small">Passe o mouse sobre um indicador para ver o que ele significa.</p>`
        : `<p class="empty">Fundamentos indisponíveis para este ativo.</p>`}
      </article>
    </div>

    <article class="panel"><h2>Análise</h2><div id="analysis"></div></article>`;

  drawPrice(root, data.history, q);
  setupWatch(root, q, data.watchlist_id);
  aiPanel($("#analysis", root), {
    label: "Analisar com IA",
    path: `/api/asset/${encodeURIComponent(q.ticker)}/analysis`,
    emptyHint: "A IA lê os números desta página e escreve uma análise técnica e fundamentalista.",
  });

  root.querySelectorAll("input[name=period]").forEach((r) => r.addEventListener("change", async () => {
    $("#price-chart", root).innerHTML = `<p class="empty">Carregando…</p>`;
    try {
      const pts = await api(`/api/asset/${encodeURIComponent(q.ticker)}/history?period=${r.value}`);
      drawPrice(root, pts, q);
    } catch (e) {
      $("#price-chart", root).innerHTML = `<p class="empty">${esc(e.message)}</p>`;
    }
  }));
}

function drawPrice(root, points, q) {
  const first = points[0], last = points.at(-1);
  $("#period-change", root).innerHTML = first && last
    ? `No período: ${changeHtml(((last.close - first.close) / first.close) * 100)}, de ${money(first.close, q.currency)} para ${money(last.close, q.currency)}.`
    : "";
  lineChart($("#price-chart", root), [{ name: q.ticker, color: "var(--brand)", points: points.map((p) => ({ date: p.date, value: p.close })) }],
    { yFormat: (v) => money(v, q.currency), area: true, label: `Preço de ${q.ticker}` });
}

function setupWatch(root, q, initialId) {
  let watchId = initialId;
  const btn = $("#watch-btn", root);
  const paint = () => {
    btn.innerHTML = watchId ? `${icon("check")}<span>Na watchlist</span>` : `${icon("eye")}<span>Adicionar à watchlist</span>`;
    btn.title = watchId ? "Clique para remover da watchlist" : "";
  };
  paint();
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    try {
      if (watchId) {
        await api(`/api/watchlist/${watchId}`, { method: "DELETE" });
        watchId = null;
        toast(`${q.ticker} removido da watchlist.`);
      } else {
        watchId = (await api("/api/watchlist", { method: "POST", body: { ticker: q.ticker } })).id;
        toast(`${q.ticker} adicionado à watchlist.`);
      }
      paint();
    } catch (e) {
      toast(e.message, "error");
    } finally {
      btn.disabled = false;
    }
  });
}

async function renderPicker(root) {
  root.innerHTML = `
    <h1 class="page-title">Ativos</h1>
    <form class="inline-form" id="asset-form">
      <label class="field grow"><span>Ticker</span>
        <input name="ticker" placeholder="Ex.: PETR4, VALE3, AAPL" autocomplete="off" required autofocus></label>
      <button class="btn btn-primary" type="submit">Abrir</button>
    </form>
    <h2 class="section-title">Da sua watchlist</h2>
    <div id="chips" class="chips"><p class="muted">Carregando…</p></div>`;
  $("#asset-form", root).addEventListener("submit", (e) => {
    e.preventDefault();
    const t = new FormData(e.target).get("ticker").trim().toUpperCase();
    if (t) location.hash = `#ativos/${encodeURIComponent(t)}`;
  });
  try {
    const rows = await api("/api/watchlist");
    $("#chips", root).innerHTML = rows.length
      ? rows.map((r) => `<a class="chip" href="#ativos/${encodeURIComponent(r.ticker)}">${esc(r.ticker)} ${changeHtml(r.change_percent)}</a>`).join("")
      : `<p class="empty">A watchlist está vazia.</p>`;
  } catch {
    $("#chips", root).innerHTML = "";
  }
}
