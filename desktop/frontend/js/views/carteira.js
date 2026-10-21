// Carteira: posições com preço médio e cotação, proventos e operações; importação da B3.

import { api, brl, brlCompact, changeHtml, confirmDialog, esc, exportReport, formDialog, fullDate, icon, money, num, toast, todayIso, valuesHidden, $ } from "../core.js";
import { groupedBars, lineChart } from "../charts.js";

const KINDS = [
  ["buy", "Compra"], ["sell", "Venda"], ["dividend", "Dividendo"], ["jcp", "Juros sobre capital próprio"],
  ["income", "Rendimento (FII)"], ["bonus", "Desdobramento ou bonificação"], ["grouping", "Grupamento"],
];
const INCOME = new Set(["dividend", "jcp", "income"]);
const OPS_PAGE = 30;

// Cotas também dizem quanto a pessoa tem: somem junto com os valores
const qty = (v) => (valuesHidden() ? "••" : num(v, Number.isInteger(v) ? 0 : 2));

export async function render(root) {
  root.innerHTML = `
    <div class="page-head">
      <h1 class="page-title">Carteira</h1>
      <div class="toolbar">
        <label class="btn" for="b3-input">${icon("upload")}<span>Importar da B3</span></label>
        <input id="b3-input" type="file" accept=".xlsx,.xls,.csv" multiple hidden>
        <button class="btn" type="button" id="ir-btn">${icon("download")}<span>Relatório do IR</span></button>
        <button class="btn btn-primary" type="button" id="op-add">${icon("plus")}<span>Lançar operação</span></button>
      </div>
    </div>
    <div class="kpis" id="pf-kpis"></div>
    <div id="pf-warnings"></div>
    <article class="panel"><h2>Posições</h2><div id="pf-positions"><p class="empty">Buscando cotações…</p></div></article>
    <div class="grid" id="pf-perf-row" hidden>
      <article class="panel panel-wide"><h2>Rentabilidade comparada</h2><div class="chart" id="pf-perf-chart"></div></article>
      <article class="panel"><h2>Por período</h2><div id="pf-perf-table"></div></article>
    </div>
    <div class="grid">
      <article class="panel panel-wide"><h2>Proventos nos últimos 12 meses</h2><div class="chart chart-bars" id="pf-income"></div></article>
      <article class="panel">
        <h2>Como importar da B3</h2>
        <ol class="steps">
          <li>Entre em <strong>investidor.b3.com.br</strong> e abra <strong>Extratos</strong>.</li>
          <li>Em <strong>Negociação</strong>, escolha o período e baixe em Excel: são as compras e vendas.</li>
          <li>Em <strong>Movimentação</strong>, faça o mesmo: são os dividendos, JCP, rendimentos e desdobramentos.</li>
          <li>Clique em <strong>Importar da B3</strong> ou arraste os arquivos para a janela.</li>
        </ol>
        <p class="muted small">Importar o mesmo período de novo não duplica nada. A B3 só tem o histórico desde
        novembro de 2019; compras anteriores você lança à mão.</p>
      </article>
    </div>
    <article class="panel"><div class="panel-head"><h2>Operações</h2></div><div id="pf-ops"></div></article>`;

  $("#op-add", root).addEventListener("click", () => addOperation(root));
  $("#ir-btn", root).addEventListener("click", () => exportReport({
    title: "Relatório para o Imposto de Renda", path: "/api/export/ir", year: new Date().getFullYear() - 1,
    intro: "Posição em 31/12 pelo custo (bens e direitos), proventos e vendas do ano-calendário. Confira com os informes das corretoras antes de declarar.",
  }));
  $("#b3-input", root).addEventListener("change", async (e) => {
    const files = [...e.target.files];
    e.target.value = "";
    for (const f of files) await importB3(f);
    if (files.length) load(root);
  });
  load(root);
}

async function load(root) {
  loadOperations(root);
  loadPerformance(root);
  let o;
  try {
    o = await api("/api/portfolio");
  } catch (e) {
    $("#pf-positions", root).innerHTML = `<p class="empty">Não foi possível carregar a carteira: ${esc(e.message)}</p>`;
    return;
  }
  renderKpis(root, o.totals);
  renderWarnings(root, o.totals);
  renderPositions(root, o);
  renderIncome(root, o.income_by_month);
}

function renderKpis(root, t) {
  const el = $("#pf-kpis", root);
  if (!t.operation_count) { el.innerHTML = ""; return; }
  const up = t.result >= 0;
  el.innerHTML = `
    <div class="kpi">
      <span class="kpi-label">${icon("pie")} Valor da carteira</span>
      <strong class="kpi-value">${brl(t.market_value)}</strong>
      <span class="kpi-sub">investido ${brl(t.invested)}</span>
    </div>
    <div class="kpi">
      <span class="kpi-label">${icon("chart")} Resultado</span>
      <strong class="kpi-value ${up ? "up" : "down"}">${up ? "▲" : "▼"}&nbsp;${brl(Math.abs(t.result))}</strong>
      <span class="kpi-sub">${t.result_percent == null ? "sem cotação agora" : `${up ? "+" : "−"}${num(Math.abs(t.result_percent), 1)}% sobre o preço médio`}${
        t.realized ? ` · vendas: ${t.realized >= 0 ? "lucro" : "prejuízo"} de ${brl(Math.abs(t.realized))}` : ""}</span>
    </div>
    <div class="kpi">
      <span class="kpi-label">${icon("receipt")} Proventos em 12 meses</span>
      <strong class="kpi-value">${brl(t.income_12m)}</strong>
      <span class="kpi-sub">${brl(t.income_total)} desde a primeira operação</span>
    </div>`;
}

function renderWarnings(root, t) {
  const items = [];
  if (t.missing_quotes) {
    items.push(["Cotação indisponível", `${t.missing_quotes === 1 ? "Um ativo entrou" : `${t.missing_quotes} ativos entraram`} no valor da carteira pelo preço médio. Verifique a internet e abra a tela de novo.`]);
  }
  if (t.incomplete.length) {
    items.push(["Faltam compras antigas", `Há vendas de ${t.incomplete.join(", ")} maiores que as compras lançadas. Lance as compras anteriores para o preço médio e o lucro ficarem certos.`]);
  }
  $("#pf-warnings", root).innerHTML = items.length ? `<ul class="alert-list">${items.map(([title, msg]) => `
    <li class="alert">${icon("alert")}<div><p class="alert-title">${esc(title)}</p><p>${esc(msg)}</p></div></li>`).join("")}</ul>` : "";
}

function renderPositions(root, o) {
  const el = $("#pf-positions", root);
  if (!o.totals.operation_count) {
    el.innerHTML = `<p class="empty">Nenhuma operação ainda. Importe os extratos da B3 ou lance uma compra à mão.</p>`;
    return;
  }
  if (!o.positions.length) {
    el.innerHTML = `<p class="empty">Nenhuma posição aberta: tudo o que foi comprado já foi vendido.</p>`;
    return;
  }
  el.innerHTML = `<div class="table-scroll"><table class="table">
    <thead><tr><th>Ativo</th><th class="num">Cotas</th><th class="num">Preço médio</th><th class="num">Cotação</th>
      <th class="num">Valor</th><th class="num">Resultado</th><th class="num">Na carteira</th><th class="num">Proventos 12m</th></tr></thead>
    <tbody>${o.positions.map((p) => `<tr>
      <td><a class="ticker" href="#ativos/${encodeURIComponent(p.ticker)}">${esc(p.ticker)}</a><span class="ticker-name pf-name" title="${esc(p.name)}">${esc(p.name)}</span></td>
      <td class="num">${qty(p.quantity)}</td>
      <td class="num">${brl(p.avg_price)}</td>
      <td class="num">${p.price == null ? `<span class="muted">indisponível</span>` : `${money(p.price)} ${changeHtml(p.change_percent)}`}</td>
      <td class="num">${brl(p.market_value)}</td>
      <td class="num">${p.result == null ? "—" : `<span class="${p.result >= 0 ? "up" : "down"}">${p.result >= 0 ? "▲" : "▼"} ${brl(Math.abs(p.result))}</span>
        <span class="muted small">${p.result_percent == null ? "" : `${p.result_percent >= 0 ? "+" : "−"}${num(Math.abs(p.result_percent), 1)}%`}</span>`}</td>
      <td class="num">${num(p.weight, 1)}%</td>
      <td class="num">${p.income_12m ? brl(p.income_12m) : "—"}</td>
    </tr>`).join("")}</tbody></table></div>
    ${o.closed.length ? `<p class="muted small">Posições encerradas: ${o.closed.map((c) =>
      `${esc(c.ticker)} (${c.realized >= 0 ? "lucro" : "prejuízo"} de ${brl(Math.abs(c.realized))})`).join(", ")}.</p>` : ""}`;
}

function renderIncome(root, months) {
  const el = $("#pf-income", root);
  if (months.every((m) => !m.amount)) {
    el.innerHTML = `<p class="empty">Nenhum provento nos últimos 12 meses. Eles vêm do extrato de Movimentação da B3.</p>`;
    return;
  }
  groupedBars(el, months.map((m) => ({
    label: new Intl.DateTimeFormat("pt-BR", { month: "short" }).format(new Date(m.year, m.month - 1, 1)).replace(".", ""),
    values: [m.amount],
  })), [{ name: "Proventos", color: "var(--series-1)" }],
  { yFormat: brlCompact, tooltipFormat: brl, label: "Proventos recebidos por mês" });
}

// Retorno ponderado no tempo: aportes e resgates não contam como ganho (docs/CARTEIRA.md, seção 5)
const monthYear = (iso) => new Intl.DateTimeFormat("pt-BR", { month: "short", year: "numeric" })
  .format(new Date(String(iso).slice(0, 10) + "T12:00:00")).replace(".", "");
const signedPct = (v, digits = 1) => (v == null ? "—" : `${v >= 0 ? "+" : "−"}${num(Math.abs(v), digits)}%`);

async function loadPerformance(root) {
  const row = $("#pf-perf-row", root);
  // Busca anos de preços na primeira vez: pode levar alguns segundos
  $("#pf-perf-chart", root).innerHTML = `<p class="empty">Calculando a rentabilidade…</p>`;
  let p;
  try {
    p = await api("/api/portfolio/performance");
  } catch (e) {
    row.hidden = false;
    $("#pf-perf-chart", root).innerHTML = `<p class="empty">Não foi possível calcular a rentabilidade: ${esc(e.message)}</p>`;
    return;
  }
  row.hidden = !p;
  if (!p) return;
  const line = (key, name, color) => ({ name, color, points: p.chart.filter((c) => c[key] != null).map((c) => ({ date: c.date, value: c[key] })) });
  lineChart($("#pf-perf-chart", root), [
    line("portfolio", "Carteira", "var(--series-1)"),
    line("cdi", "CDI", "var(--series-2)"),
    line("ibov", "Ibovespa", "var(--series-3)"),
  ], { yFormat: (v) => `${num(v, 0)}%`, tooltipFormat: (v) => signedPct(v, 2), baseline: 0, xFormat: monthYear,
    label: "Rentabilidade acumulada da carteira, do CDI e do Ibovespa" });

  const notes = [];
  if (!p.benchmarks.cdi) notes.push("CDI indisponível agora (Banco Central fora do ar ou sem internet).");
  if (!p.benchmarks.ibov) notes.push("Ibovespa indisponível agora.");
  if (p.without_history.length) notes.push(`Sem histórico de preços: ${p.without_history.join(", ")} (avaliado pelo preço da última operação).`);
  $("#pf-perf-table", root).innerHTML = `
    <table class="table">
      <thead><tr><th></th><th class="num">Carteira</th><th class="num">CDI</th><th class="num">Ibovespa</th></tr></thead>
      <tbody>${p.windows.map((w) => `<tr>
        <td>${esc(w.label)}</td>
        <td class="num"><strong class="${w.portfolio >= 0 ? "up" : "down"}">${signedPct(w.portfolio)}</strong></td>
        <td class="num">${signedPct(w.cdi)}</td>
        <td class="num">${signedPct(w.ibov)}</td>
      </tr>`).join("")}</tbody>
    </table>
    ${p.windows[0] && p.windows[0].cdi_share != null ? `<p class="small">Desde o início, a carteira rendeu <strong>${num(p.windows[0].cdi_share, 0)}% do CDI</strong>.</p>` : ""}
    <p class="muted small">Retorno ponderado no tempo desde ${fullDate(p.start)}: aportes e vendas não contam como ganho, só a variação dos ativos e os proventos.
      Não é o mesmo que o resultado sobre o preço médio.</p>
    ${notes.map((n) => `<p class="muted small">${esc(n)}</p>`).join("")}`;
}

async function loadOperations(root, limit = OPS_PAGE) {
  const el = $("#pf-ops", root);
  let ops;
  try {
    ops = await api("/api/portfolio/operations");
  } catch (e) {
    el.innerHTML = `<p class="empty">${esc(e.message)}</p>`;
    return;
  }
  if (!ops.length) { el.innerHTML = `<p class="empty">Nenhuma operação lançada.</p>`; return; }
  el.innerHTML = `<div class="table-scroll"><table class="table">
    <thead><tr><th>Data</th><th>Ativo</th><th>Operação</th><th class="num">Cotas</th><th class="num">Preço</th>
      <th class="num">Valor</th><th>Origem</th><th class="actions"><span class="sr-only">Ações</span></th></tr></thead>
    <tbody>${ops.slice(0, limit).map((op) => `<tr data-id="${op.id}">
      <td class="nowrap">${fullDate(op.date)}</td>
      <td><span class="ticker">${esc(op.ticker)}</span></td>
      <td>${esc(op.kind_label)}</td>
      <td class="num">${INCOME.has(op.kind) ? "—" : qty(op.quantity)}</td>
      <td class="num">${op.price ? brl(op.price) : "—"}</td>
      <td class="num ${INCOME.has(op.kind) ? "amount-in" : ""}">${op.amount ? brl(op.amount) : "—"}</td>
      <td class="muted small">${op.source === "b3" ? "B3" : "Manual"}</td>
      <td class="actions"><button class="icon-btn" data-act="delete" aria-label="Excluir ${esc(op.kind_label)} de ${esc(op.ticker)}">${icon("trash")}</button></td>
    </tr>`).join("")}</tbody></table></div>
    ${ops.length > limit ? `<button class="btn" type="button" id="ops-more">Mostrar mais (${ops.length - limit})</button>` : ""}`;

  const more = $("#ops-more", el);
  if (more) more.addEventListener("click", () => loadOperations(root, limit + OPS_PAGE * 4));
  el.querySelectorAll("button[data-act=delete]").forEach((b) => b.addEventListener("click", async () => {
    const op = ops.find((x) => String(x.id) === b.closest("tr").dataset.id);
    const ok = await confirmDialog({
      title: `Excluir ${op.kind_label.toLowerCase()} de ${op.ticker}?`,
      message: op.source === "b3"
        ? "A posição é recalculada sem ela. Se importar o mesmo extrato de novo, a operação volta."
        : "A posição é recalculada sem ela.",
      confirmLabel: "Excluir",
    });
    if (!ok) return;
    await api(`/api/portfolio/operations/${op.id}`, { method: "DELETE" });
    toast("Operação excluída.");
    load(root);
  }));
}

function addOperation(root) {
  return formDialog({
    title: "Lançar operação",
    fields: [
      { name: "kind", label: "Operação", type: "select", value: "buy", options: KINDS },
      { name: "ticker", label: "Ativo", placeholder: "Ex.: PETR4, HGLG11, BOVA11", required: true, autofocus: true },
      { name: "date", label: "Data", type: "date", required: true, value: todayIso() },
      { name: "quantity", label: "Cotas", type: "number", step: "any", min: "0" },
      { name: "price", label: "Preço por cota (R$)", type: "number", step: "0.01", min: "0" },
      { name: "fees", label: "Taxas e corretagem (R$)", type: "number", step: "0.01", min: "0" },
      { name: "amount", label: "Valor recebido (R$)", type: "number", step: "0.01", min: "0" },
    ],
    submitLabel: "Lançar",
    onOpen: (form) => {
      // Cada tipo de operação pede campos diferentes
      const show = () => {
        const kind = form.elements.kind.value;
        const visible = INCOME.has(kind) ? ["amount"]
          : kind === "grouping" ? ["quantity"]
          : kind === "bonus" ? ["quantity", "price"]
          : ["quantity", "price", "fees"];
        for (const name of ["quantity", "price", "fees", "amount"]) {
          form.elements[name].closest(".field").hidden = !visible.includes(name);
        }
        form.elements.quantity.closest(".field").firstElementChild.textContent =
          kind === "grouping" ? "Cotas que deixaram de existir" : kind === "bonus" ? "Cotas recebidas" : "Cotas";
        form.elements.price.closest(".field").firstElementChild.textContent =
          kind === "bonus" ? "Custo por cota (R$, 0 em desdobramento)" : "Preço por cota (R$)";
      };
      form.elements.kind.addEventListener("change", show);
      show();
    },
    onSubmit: async (v) => {
      const n = (x) => (x ? Number(x) : 0);
      const op = await api("/api/portfolio/operations", { method: "POST", body: {
        kind: v.kind, ticker: v.ticker.trim(), date: v.date,
        quantity: n(v.quantity), price: n(v.price), fees: n(v.fees), amount: n(v.amount),
      } });
      toast(`${op.kind_label} de ${op.ticker} lançada.`);
      load(root);
      return op;
    },
  });
}

// Usada também pelo arrastar e soltar da janela (main.js)
export async function importB3(file) {
  toast(`Importando ${file.name}…`);
  try {
    const r = await api(`/api/portfolio/import?filename=${encodeURIComponent(file.name)}`, { method: "POST", raw: file });
    const which = r.file_type === "negociacao" ? "Negociação" : "Movimentação";
    const parts = [`${r.imported} ${r.imported === 1 ? "operação importada" : "operações importadas"} do extrato de ${which}`];
    if (r.duplicates) parts.push(`${r.duplicates} já ${r.duplicates === 1 ? "estava" : "estavam"} na carteira`);
    toast(`${parts.join(", ")}.`);
    const skipped = r.skipped.filter((s) => !s.reason.startsWith("Compras e vendas"));
    if (skipped.length) {
      toast(`Não importado: ${skipped.map((s) => `${s.count} ${s.reason.toLowerCase()}`).join("; ")}.`, "info");
    }
    return r;
  } catch (e) {
    toast(`Não foi possível importar: ${e.message}`, "error");
    return null;
  }
}
