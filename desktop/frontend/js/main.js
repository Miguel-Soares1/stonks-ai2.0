// Ponto de entrada: roteamento por hash, tema, ocultar valores, bloqueio por PIN,
// status da IA, conversa flutuante, busca (Ctrl K) e importação por arrastar.

import { api, setHideValues, valuesHidden, $, $$ } from "./core.js";
import { ask, mountChat } from "./chat.js";
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
  if (!$("#lock-screen").hidden) return;
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
    await mod.render(section, params, { refreshStatus: loadStatus, applyLockStatus });
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
    $("#chat-drawer-status").textContent = s.llm.available ? ` · ${detail}` : " · IA desconectada";
    el.title = `Dados em: ${s.data_dir}`;
  } catch {
    el.className = "ai-status off";
    $("#ai-label").textContent = "Status da IA indisponível";
  }
}

// ── Ocultar valores ─────────────────────────────────────

function applyHideValues(on) {
  setHideValues(on);
  const btn = $("#hide-toggle");
  btn.setAttribute("aria-pressed", String(on));
  btn.title = on ? "Mostrar valores" : "Ocultar valores";
  btn.setAttribute("aria-label", btn.title);
  $("use", btn).setAttribute("href", on ? "#i-eye-off" : "#i-eye");
}
$("#hide-toggle").addEventListener("click", () => {
  applyHideValues(!valuesHidden());
  api("/api/settings/hide-values", { method: "PUT", body: { hide_values: valuesHidden() } }).catch(() => {});
  route(); // redesenha a tela com os valores mascarados (ou não)
});

// ── Bloqueio por PIN ────────────────────────────────────

const lockScreen = $("#lock-screen");

function showLock() {
  if (!lockScreen.hidden) return;
  closeChat();
  outlet.replaceChildren(); // nada de dados por trás da tela de bloqueio
  lockScreen.hidden = false;
  $("#lock-error").hidden = true;
  $("#lock-pin").value = "";
  $("#lock-pin").focus();
}

function applyLockStatus(lock) {
  $("#lock-now").hidden = !lock.enabled;
  if (lock.locked) showLock();
}

window.addEventListener("stonks:locked", showLock);
$("#lock-now").addEventListener("click", async () => {
  await api("/api/lock/lock", { method: "POST" }).catch(() => {});
  showLock();
});
$("#lock-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const err = $("#lock-error");
  try {
    await api("/api/lock/unlock", { method: "POST", body: { pin: $("#lock-pin").value } });
    lockScreen.hidden = true;
    route();
    loadStatus();
  } catch (ex) {
    err.textContent = ex.message;
    err.hidden = false;
    $("#lock-pin").value = "";
    $("#lock-pin").focus();
  }
});

// ── Conversa flutuante ──────────────────────────────────

const drawer = $("#chat-drawer");
let drawerChat = null;

function openChat() {
  if (!drawerChat) drawerChat = mountChat($("#chat-drawer-body"), { compact: true });
  drawer.hidden = false;
  $("#chat-open").setAttribute("aria-expanded", "true");
  drawerChat.focus();
}
function closeChat() {
  drawer.hidden = true;
  $("#chat-open").setAttribute("aria-expanded", "false");
}
$("#chat-open").addEventListener("click", () => (drawer.hidden ? openChat() : closeChat()));
$("#chat-close").addEventListener("click", closeChat);
$("#chat-expand").addEventListener("click", closeChat);
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !drawer.hidden) closeChat(); });
// Botões "Entender com a IA" das telas mandam a pergunta pronta
window.addEventListener("stonks:ask", (e) => { openChat(); ask(e.detail); });

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

// Tema, máscara e bloqueio antes da primeira tela; o status da IA (mais lento) vem em paralelo
(async () => {
  try {
    const b = await api("/api/boot");
    applyTheme(b.theme);
    applyHideValues(b.hide_values);
    applyLockStatus(b.lock);
  } catch { /* segue sem as preferências */ }
  route();
  loadStatus();
})();
