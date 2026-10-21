// Gráficos em SVG puro. Regras: eixo único, linhas de 2px, grade discreta,
// tooltip com crosshair; com 2+ séries há legenda e rótulo direto no fim de cada linha.

import { $, esc, shortDate } from "./core.js";

const DAY = 86400000;

export function niceTicks(min, max, count = 4) {
  if (min === max) { min -= 1; max += 1; }
  const raw = (max - min) / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const norm = raw / mag;
  const step = (norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10) * mag;
  const ticks = [];
  for (let t = Math.floor(min / step) * step; t <= Math.ceil(max / step) * step + step / 2; t += step) {
    ticks.push(Math.round(t * 1e6) / 1e6);
  }
  return ticks;
}

const toTime = (d) => new Date(String(d).slice(0, 10) + "T12:00:00").getTime();

function nearest(points, t) {
  let lo = 0, hi = points.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (points[mid].t < t) lo = mid + 1; else hi = mid;
  }
  if (lo > 0 && Math.abs(points[lo - 1].t - t) < Math.abs(points[lo].t - t)) lo -= 1;
  return points[lo];
}

/**
 * series: [{ name, color, points: [{ date, value }] }]
 * opts: { yFormat, tooltipFormat, xFormat, area, baseline, height }
 */
export function lineChart(el, series, opts = {}) {
  const yFormat = opts.yFormat || ((v) => v.toLocaleString("pt-BR"));
  const tipFormat = opts.tooltipFormat || yFormat;
  const xFormat = opts.xFormat || shortDate;
  const prepared = series
    .map((s) => ({ ...s, points: s.points.map((p) => ({ t: toTime(p.date), date: p.date, v: p.value })) }))
    .filter((s) => s.points.length);
  if (!prepared.length) {
    el.innerHTML = `<p class="empty">${opts.emptyMessage || "Sem dados para o período."}</p>`;
    return;
  }

  const multi = prepared.length > 1;
  const render = () => {
    const w = el.clientWidth;
    if (!el.isConnected || !w) return; // fora da tela ou sem largura ainda; o observador redesenha
    const h = opts.height || 240;
    const pad = { l: 72, r: multi ? 64 : 12, t: 10, b: 26 };
    const all = prepared.flatMap((s) => s.points);
    const vals = all.map((p) => p.v);
    if (opts.baseline != null) vals.push(opts.baseline);
    const ticks = niceTicks(Math.min(...vals), Math.max(...vals));
    const lo = ticks[0], hi = ticks[ticks.length - 1];
    const t0 = Math.min(...all.map((p) => p.t));
    const t1 = Math.max(...all.map((p) => p.t));
    const x = (t) => pad.l + ((t - t0) / (t1 - t0 || DAY)) * (w - pad.l - pad.r);
    const y = (v) => pad.t + ((hi - v) / (hi - lo || 1)) * (h - pad.t - pad.b);

    const paths = prepared.map((s) => {
      const d = s.points.map((p, i) => `${i ? "L" : "M"}${x(p.t).toFixed(1)},${y(p.v).toFixed(1)}`).join("");
      const areaBase = y(opts.baseline ?? lo);
      const area = opts.area && !multi
        ? `<path class="area" style="fill:${s.color}" d="${d}L${x(s.points.at(-1).t).toFixed(1)},${areaBase}L${x(s.points[0].t).toFixed(1)},${areaBase}Z"/>`
        : "";
      return `${area}<path class="series" style="stroke:${s.color}" d="${d}"/>`;
    }).join("");

    // Rótulos diretos no fim das linhas, afastados para não colidir
    let labels = "";
    if (multi) {
      const ends = prepared.map((s) => ({ name: s.name, y: y(s.points.at(-1).v) })).sort((a, b) => a.y - b.y);
      for (let i = 1; i < ends.length; i++) ends[i].y = Math.max(ends[i].y, ends[i - 1].y + 14);
      labels = ends.map((e) => `<text class="end-label" x="${w - pad.r + 8}" y="${e.y + 4}">${esc(e.name)}</text>`).join("");
    }

    const xTicks = [t0, t0 + (t1 - t0) / 2, t1];
    el.innerHTML = `
      ${multi ? `<ul class="legend">${prepared.map((s) => `<li><span class="swatch" style="background:${s.color}"></span>${esc(s.name)}</li>`).join("")}</ul>` : ""}
      <svg role="img" aria-label="${esc(opts.label || "Gráfico de linha")}" height="${h}">
        ${ticks.map((t) => `
          <line class="${t === opts.baseline ? "zero-line" : "grid-line"}" x1="${pad.l}" x2="${w - pad.r}" y1="${y(t)}" y2="${y(t)}"/>
          <text class="axis-label" x="${pad.l - 10}" y="${y(t) + 4}" text-anchor="end">${esc(yFormat(t))}</text>`).join("")}
        ${xTicks.map((t, k) => `<text class="axis-label" x="${x(t)}" y="${h - 6}"
          text-anchor="${["start", "middle", "end"][k]}">${esc(xFormat(new Date(t).toISOString()))}</text>`).join("")}
        ${paths}
        ${labels}
        <line class="crosshair" y1="${pad.t}" y2="${h - pad.b}" visibility="hidden"/>
        ${prepared.map((s, i) => `<circle class="focus" data-i="${i}" r="4.5" style="fill:${s.color}" visibility="hidden"/>`).join("")}
        <rect class="hit" x="${pad.l}" y="0" width="${Math.max(0, w - pad.l - pad.r)}" height="${h}" fill="transparent"/>
      </svg>`;

    const svg = $("svg", el);
    const cross = $(".crosshair", svg);
    const dots = [...svg.querySelectorAll(".focus")];
    const tip = $("#tooltip");
    const hit = $(".hit", svg);
    hit.addEventListener("mousemove", (ev) => {
      const box = svg.getBoundingClientRect();
      const t = t0 + ((ev.clientX - box.left - pad.l) / (w - pad.l - pad.r)) * (t1 - t0);
      const hits = prepared.map((s) => nearest(s.points, t));
      const px = x(hits[0].t);
      cross.setAttribute("x1", px); cross.setAttribute("x2", px);
      cross.setAttribute("visibility", "visible");
      hits.forEach((p, i) => {
        dots[i].setAttribute("cx", x(p.t)); dots[i].setAttribute("cy", y(p.v));
        dots[i].setAttribute("visibility", "visible");
      });
      tip.innerHTML = `<small>${shortDate(hits[0].date)}</small>` + hits.map((p, i) => multi
        ? `<div class="tip-row"><span class="swatch" style="background:${prepared[i].color}"></span>${esc(prepared[i].name)} <b>${esc(tipFormat(p.v))}</b></div>`
        : `<b>${esc(tipFormat(p.v))}</b>`).join("");
      tip.hidden = false;
      const left = box.left + px + 14;
      tip.style.left = `${left + tip.offsetWidth > innerWidth - 8 ? box.left + px - tip.offsetWidth - 14 : left}px`;
      tip.style.top = `${box.top + 8}px`;
    });
    hit.addEventListener("mouseleave", () => {
      cross.setAttribute("visibility", "hidden");
      dots.forEach((d) => d.setAttribute("visibility", "hidden"));
      tip.hidden = true;
    });
  };

  render();
  observeResize(el, render);
}

/**
 * Barras agrupadas por categoria (ex.: mês), com 2 séries.
 * groups: [{ label, values: [n, n] }], series: [{ name, color }]
 */
export function groupedBars(el, groups, series, opts = {}) {
  const yFormat = opts.yFormat || ((v) => v.toLocaleString("pt-BR"));
  const render = () => {
    const w = el.clientWidth;
    if (!el.isConnected || !w) return;
    const h = opts.height || 220;
    const pad = { l: 72, r: 8, t: 10, b: 26 };
    const max = Math.max(1, ...groups.flatMap((g) => g.values));
    const ticks = niceTicks(0, max);
    const hi = ticks.at(-1);
    const y = (v) => pad.t + ((hi - v) / hi) * (h - pad.t - pad.b);
    const band = (w - pad.l - pad.r) / groups.length;
    const barW = Math.min(22, (band - 16) / series.length - 2);
    const bars = groups.map((g, gi) => {
      const cx = pad.l + band * gi + band / 2;
      const start = cx - (series.length * (barW + 2)) / 2;
      return g.values.map((v, si) => {
        const bx = start + si * (barW + 2);
        const top = y(v);
        const bh = Math.max(0, y(0) - top);
        const r = Math.min(4, bh);
        // Topo arredondado, base reta no eixo
        return `<path class="bar" data-g="${gi}" style="fill:${series[si].color}"
          d="M${bx},${y(0)}V${top + r}Q${bx},${top} ${bx + r},${top}H${bx + barW - r}Q${bx + barW},${top} ${bx + barW},${top + r}V${y(0)}Z"/>`;
      }).join("") + `<text class="axis-label" x="${cx}" y="${h - 6}" text-anchor="middle">${esc(g.label)}</text>`;
    }).join("");

    el.innerHTML = `
      <ul class="legend">${series.map((s) => `<li><span class="swatch" style="background:${s.color}"></span>${esc(s.name)}</li>`).join("")}</ul>
      <svg role="img" aria-label="${esc(opts.label || "Gráfico de barras")}" height="${h}">
        ${ticks.map((t) => `
          <line class="grid-line" x1="${pad.l}" x2="${w - pad.r}" y1="${y(t)}" y2="${y(t)}"/>
          <text class="axis-label" x="${pad.l - 10}" y="${y(t) + 4}" text-anchor="end">${esc(yFormat(t))}</text>`).join("")}
        ${bars}
        ${groups.map((g, gi) => `<rect class="hit" data-g="${gi}" x="${pad.l + band * gi}" y="0" width="${band}" height="${h}" fill="transparent"/>`).join("")}
      </svg>`;

    const tip = $("#tooltip");
    el.querySelectorAll(".hit").forEach((r) => {
      r.addEventListener("mousemove", (ev) => {
        const g = groups[+r.dataset.g];
        el.querySelectorAll(".bar").forEach((b) => b.classList.toggle("dim", b.dataset.g !== r.dataset.g));
        tip.innerHTML = `<small>${esc(g.label)}</small>` + g.values.map((v, i) =>
          `<div class="tip-row"><span class="swatch" style="background:${series[i].color}"></span>${esc(series[i].name)} <b>${esc((opts.tooltipFormat || yFormat)(v))}</b></div>`).join("");
        tip.hidden = false;
        tip.style.left = `${Math.min(ev.clientX + 14, innerWidth - tip.offsetWidth - 8)}px`;
        tip.style.top = `${ev.clientY - 20}px`;
      });
      r.addEventListener("mouseleave", () => {
        el.querySelectorAll(".bar").forEach((b) => b.classList.remove("dim"));
        tip.hidden = true;
      });
    });
  };
  render();
  observeResize(el, render);
}

// Redesenha quando o contêiner muda de largura (sem acumular observadores)
function observeResize(el, render) {
  if (el._ro) el._ro.disconnect();
  let last = el.clientWidth;
  let timer;
  el._ro = new ResizeObserver(() => {
    if (!el.isConnected) { el._ro.disconnect(); return; }
    if (el.clientWidth === last) return;
    last = el.clientWidth;
    clearTimeout(timer);
    timer = setTimeout(render, 80);
  });
  el._ro.observe(el);
}
