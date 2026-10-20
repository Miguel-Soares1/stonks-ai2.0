// Ponto de entrada: roteamento por hash, tema, status da IA, busca (Ctrl K) e importação por arrastar.

import { api, $, $$ } from "./core.js";
import { importFile } from "./views/transacoes.js";

// Cada tela é um módulo carregado na primeira visita
const ROUTES = {
  inicio: () => import("./views/inicio.js"),
  ativos: () => import("./views/ativos.js"),
  watchlist: () => import("./views/watchlist.js"),
  comparar: () => import("./views/comparar.js"),
  transacoes: () => import("./views/transacoes.js"),
  orcamento: () => import("./views/orcamento.js"),
  contas: () => import("./views/contas.js"),
  metas: () => import("./views/metas.js"),
  alertas: () => import("./views/alertas.js"),
  assistente: () => import("./views/assistente.js"),
  ajustes: () => import("./views/ajustes.js"),
};

const outlet = $("#view");
let navToken = 0;

async function route() {
  const [name = "inicio", ...params] = location.hash.slice(1).split("/").map(decodeURIComponent);
  const view = ROUTES[name] ? name : "inicio";
  $$(".nav-item").forEach((a) => {
    if (a.dataset.view === view) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
  $("#tooltip").hidden = true;

  // Cada navegação ganha um contêiner novo; respostas de telas antigas não sobrescrevem a atual
  const token = ++navToken;
  const section = document.createElement("section");
  section.className = "view";
  outlet.replaceChildren(section);
  outlet.parentElement.scrollTop = 0;
  try {
    const mod = await ROUTES[view]();
    if (token !== navToken) return;
    await mod.render(section, params, { refreshStatus: loadStatus });
  } catch (e) {
    if (token === navToken) section.innerHTML = `<p class="empty">Erro ao abrir a tela: ${e.message}</p>`;
    console.error(e);
  }
}

window.addEventListener("hashchange", route);

// ── Tema ────────────────────────────────────────────────

// A preferência fica no config.yaml (a janela roda em modo privado e não guarda localStorage)
function applyTheme(theme) {
  if (theme === "light" || theme === "dark") document.documentElement.dataset.theme = theme;
  else delete document.documentElement.dataset.theme;
}
const isDark = () => {
  const t = document.documentElement.dataset.theme;
  return t ? t === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
};
$("#theme-toggle").addEventListener("click", () => {
  const next = isDark() ? "light" : "dark";
  applyTheme(next);
  api("/api/settings/theme", { method: "PUT", body: { theme: next } }).catch(() => {});
});

// ── Status da IA ────────────────────────────────────────

async function loadStatus() {
  const el = $("#ai-status");
  try {
    const s = await api("/api/status");
    applyTheme(s.theme);
    const detail = [s.llm.provider, s.llm.model].filter(Boolean).join(", ");
    el.className = "ai-status " + (s.llm.available ? "on" : "off");
    $("#ai-label").textContent = s.llm.available ? "IA conectada" : "IA desconectada";
    $("#ai-detail").textContent = detail;
    el.title = `Dados em: ${s.data_dir}`;
  } catch {
    el.className = "ai-status off";
    $("#ai-label").textContent = "Status da IA indisponível";
  }
}

// ── Busca de ativo (Ctrl K) ─────────────────────────────

const dialog = $("#search-dialog");
function openSearch() {
  if (dialog.open) return;
  $("#search-input").value = "";
  dialog.showModal();
  $("#search-input").focus();
}
$("#search-open").addEventListener("click", openSearch);
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); openSearch(); }
});
dialog.addEventListener("click", (e) => { if (e.target === dialog) dialog.close(); });
$("#search-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const ticker = $("#search-input").value.trim().toUpperCase();
  if (!ticker) return;
  dialog.close();
  location.hash = `#ativos/${encodeURIComponent(ticker)}`;
});

// ── Importar extrato arrastando para a janela ───────────

const overlay = $("#drop-overlay");
let dragDepth = 0;
const hasFiles = (e) => [...(e.dataTransfer?.types || [])].includes("Files");
window.addEventListener("dragenter", (e) => {
  if (!hasFiles(e)) return;
  e.preventDefault();
  dragDepth += 1;
  overlay.hidden = false;
});
window.addEventListener("dragover", (e) => { if (hasFiles(e)) e.preventDefault(); });
window.addEventListener("dragleave", () => {
  dragDepth = Math.max(0, dragDepth - 1);
  if (!dragDepth) overlay.hidden = true;
});
window.addEventListener("drop", async (e) => {
  if (!hasFiles(e)) return;
  e.preventDefault();
  dragDepth = 0;
  overlay.hidden = true;
  const file = e.dataTransfer.files[0];
  if (!file) return;
  const result = await importFile(file);
  if (result && result.imported) {
    if (location.hash.startsWith("#transacoes")) route();
    else location.hash = "#transacoes";
  }
});

route();
loadStatus();
