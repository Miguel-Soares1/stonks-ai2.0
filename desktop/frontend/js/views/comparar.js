// Comparar: desempenho relativo (base 100), indicadores lado a lado e comparação pela IA.

import { aiPanel, api, changeHtml, esc, money, num, toast, $ } from "../core.js";
import { lineChart } from "../charts.js";

// Ordem fixa: a cor acompanha a posição do ticker na lista, nunca o ranking
const COLORS = ["var(--series-1)", "var(--series-2)", "var(--series-3)", "var(--series-4)", "var(--series-5)"];
const PERIODS = [["1mo", "1M"], ["3mo", "3M"], ["6mo", "6M"], ["1y", "1A"], ["2y", "2A"]];
// DY e ROE chegam como fração (0,061 = 6,1%)
const pctOrDash = (v) => (v == null ? "—" : `${num(v * 100, 1)}%`);

let period = "6mo";

export async function render(root, params) {
  const preset = (params[0] || "").toUpperCase();
  root.innerHTML = `
    <h1 class="page-title">Comparar</h1>
    <form class="inline-form" id="cmp-form">
      <label class="field grow"><span>De 2 a 5 tickers, separados por vírgula ou espaço</span>
        <input name="tickers" value="${esc(preset.replaceAll(",", ", "))}" placeholder="Ex.: PETR4, VALE3, ITUB4" autocomplete="off" required></label>
      <button class="btn btn-primary" type="submit">Comparar</button>
    </form>
    <div id="result" class="stack"></div>`;

  $("#cmp-form", root).addEventListener("submit", (e) => {
    e.preventDefault();
    const list = parse(new FormData(e.target).get("tickers"));
    if (list.length < 2) { toast("Informe pelo menos 2 tickers.", "error"); return; }
    const target = `#comparar/${list.join(",")}`;
    if (location.hash === target) load(root, list);
    else location.hash = target;
  });
  const list = parse(preset);
  if (list.length >= 2) load(root, list);
  else if (list.length === 1) $("input[name=tickers]", root).focus();
}

const parse = (s) => [...new Set(String(s || "").toUpperCase().split(/[\s,;]+/).filter(Boolean))].slice(0, 5);

async function load(root, tickers) {
  const el = $("#result", root);
  el.innerHTML = `<p class="muted">Buscando ${esc(tickers.join(", "))}…</p>`;
  let items;
  try {
    items = await api(`/api/compare?tickers=${encodeURIComponent(tickers.join(","))}&period=${period}`);
  } catch (e) {
    el.innerHTML = `<p class="empty">${esc(e.message)}</p>`;
    return;
  }
  const ok = items.filter((i) => !i.error);
  const failed = items.filter((i) => i.error);

  el.innerHTML = `
    ${failed.length ? `<p class="form-error">Não encontrado: ${failed.map((f) => esc(f.ticker)).join(", ")}.</p>` : ""}
    <article class="panel">
      <div class="panel-head">
        <h2>Desempenho no período (base 100)</h2>
        <div class="seg" role="radiogroup" aria-label="Período">
          ${PERIODS.map(([v, l]) => `<label><input type="radio" name="cmp-period" value="${v}" ${v === period ? "checked" : ""}><span>${l}</span></label>`).join("")}
        </div>
      </div>
      <p class="muted small">Todos os ativos começam em 100 no início do período. Uma linha em 120 significa alta de 20%.</p>
      <div class="chart chart-tall" id="cmp-chart"></div>
    </article>
    <article class="panel">
      <h2>Indicadores</h2>
      <div class="table-scroll"><table class="table">
        <thead><tr><th>Ativo</th><th class="num">Preço</th><th class="num">Dia</th><th class="num">Período</th>
          <th class="num">P/L</th><th class="num">P/VP</th><th class="num">Dividend yield</th><th class="num">ROE</th></tr></thead>
        <tbody>${ok.map((i) => {
          const s = i.series;
          const periodChange = s.length ? s.at(-1).value - 100 : null;
          const f = i.fundamentals || {};
          const color = COLORS[items.indexOf(i)];
          return `<tr>
            <td><span class="swatch" style="background:${color}"></span><a class="ticker" href="#ativos/${encodeURIComponent(i.ticker)}">${esc(i.ticker)}</a></td>
            <td class="num">${money(i.quote.price, i.quote.currency)}</td>
            <td class="num">${changeHtml(i.quote.change_percent)}</td>
            <td class="num">${changeHtml(periodChange, 1)}</td>
            <td class="num">${f.pe_ratio != null ? num(f.pe_ratio) : "—"}</td>
            <td class="num">${f.pb_ratio != null ? num(f.pb_ratio) : "—"}</td>
            <td class="num">${pctOrDash(f.dividend_yield)}</td>
            <td class="num">${pctOrDash(f.roe)}</td>
          </tr>`;
        }).join("")}</tbody>
      </table></div>
    </article>
    <article class="panel"><h2>Comparação</h2><div id="cmp-ai"></div></article>`;

  lineChart($("#cmp-chart", el), ok.map((i) => ({
    name: i.ticker, color: COLORS[items.indexOf(i)],
    points: i.series.map((p) => ({ date: p.date, value: p.value })),
  })), { yFormat: (v) => num(v, 0), tooltipFormat: (v) => num(v, 1), baseline: 100, height: 300, label: "Desempenho relativo, base 100" });

  el.querySelectorAll("input[name=cmp-period]").forEach((r) => r.addEventListener("change", () => {
    period = r.value;
    load(root, tickers);
  }));

  if (ok.length >= 2) {
    aiPanel($("#cmp-ai", el), {
      label: "Comparar com IA",
      path: `/api/compare/analysis?tickers=${encodeURIComponent(ok.map((i) => i.ticker).join(","))}`,
      emptyHint: "A IA compara preço, variação, P/L e dividend yield e ordena os ativos por risco e retorno.",
    });
  }
}
