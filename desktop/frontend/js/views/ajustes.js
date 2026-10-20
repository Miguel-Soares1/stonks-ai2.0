// Ajustes: qual IA usar (local ou remota) e informações do sistema.

import { api, esc, toast, $ } from "../core.js";

const PROVIDERS = [
  ["ollama", "Ollama (no seu computador)"],
  ["deepseek", "DeepSeek (nuvem)"],
  ["openai", "OpenAI (nuvem)"],
  ["openai_compatible", "Outro compatível com OpenAI (nuvem)"],
];

export async function render(root, _params, { refreshStatus }) {
  root.innerHTML = `<h1 class="page-title">Ajustes</h1><p class="muted">Carregando…</p>`;
  let s, models;
  try {
    [s, models] = await Promise.all([api("/api/settings"), api("/api/settings/ollama-models")]);
  } catch (e) {
    root.innerHTML = `<h1 class="page-title">Ajustes</h1><p class="empty">${esc(e.message)}</p>`;
    return;
  }

  root.innerHTML = `
    <h1 class="page-title">Ajustes</h1>
    <form id="settings" class="settings">
      <article class="panel">
        <h2>Inteligência artificial</h2>
        <div class="form-grid">
          <label class="field"><span>Onde a IA roda</span>
            <select name="provider">${PROVIDERS.map(([v, l]) => `<option value="${v}" ${v === s.provider ? "selected" : ""}>${l}</option>`).join("")}</select></label>
          <div id="model-field"></div>
          <label class="field" data-for="ollama"><span>Endereço do Ollama</span><input name="endpoint" value="${esc(s.endpoint)}"></label>
          <label class="field" data-for="openai_compatible"><span>URL da API</span><input name="base_url" value="${esc(s.base_url)}" placeholder="https://..."></label>
          <label class="field" data-for="remote"><span>Chave da API</span>
            <input name="api_key" type="password" autocomplete="off" placeholder="${s.has_api_key ? "Chave salva. Deixe vazio para manter." : "Cole sua chave ou use \${NOME_DA_VARIAVEL}"}"></label>
          <label class="field"><span>Criatividade (temperatura): <output id="temp-out">${s.temperature}</output></span>
            <input name="temperature" type="range" min="0" max="1.5" step="0.1" value="${s.temperature}"></label>
          <label class="check" data-for="remote"><input type="checkbox" name="fallback_to_ollama" ${s.fallback_to_ollama ? "checked" : ""}> Usar o Ollama local se a IA na nuvem falhar</label>
        </div>
        <p class="muted small" id="privacy-note"></p>
      </article>
      <article class="panel">
        <h2>Mercado</h2>
        <label class="field narrow"><span>Bolsa padrão para tickers ambíguos</span>
          <select name="default_exchange">${["B3", "NYSE"].map((v) => `<option ${v === s.default_exchange ? "selected" : ""}>${v}</option>`).join("")}</select></label>
      </article>
      <div class="toolbar"><button class="btn btn-primary" type="submit">Salvar ajustes</button></div>
    </form>
    <article class="panel">
      <h2>Sistema</h2>
      <dl class="stats">
        <div><dt>Versão</dt><dd>${esc(s.system.version)}</dd></div>
        <div><dt>Banco de dados</dt><dd>${s.system.database_ok ? "Funcionando" : "Com problema"}</dd></div>
        <div class="span-2"><dt>Pasta dos seus dados</dt><dd class="mono">${esc(s.system.data_dir)}</dd></div>
      </dl>
    </article>`;

  const form = $("#settings", root);
  const providerSel = $("select[name=provider]", form);
  const modelField = $("#model-field", form);

  const sync = () => {
    const p = providerSel.value;
    const remote = p !== "ollama";
    form.querySelectorAll("[data-for]").forEach((el) => {
      const f = el.dataset.for;
      el.hidden = !(f === p || (f === "remote" && remote));
    });
    // No Ollama, lista os modelos instalados com o tamanho (quanto menor, menos memória)
    if (p === "ollama" && models.length) {
      const current = models.some((m) => m.name === s.model) ? s.model : models[0].name;
      modelField.innerHTML = `<label class="field"><span>Modelo</span><select name="model">${models.map((m) =>
        `<option value="${esc(m.name)}" ${m.name === current ? "selected" : ""}>${esc(m.name)} (${m.size_gb.toLocaleString("pt-BR")} GB)</option>`).join("")}</select></label>`;
    } else {
      modelField.innerHTML = `<label class="field"><span>Modelo</span><input name="model" required value="${esc(p === s.provider ? s.model : "")}"
        placeholder="${p === "deepseek" ? "deepseek-chat" : p === "openai" ? "gpt-4o-mini" : "nome-do-modelo"}"></label>`;
    }
    $("#privacy-note", form).textContent = remote
      ? "Com uma IA na nuvem, os dados usados em cada pergunta (cotações, resumos do mês) são enviados ao provedor escolhido."
      : "Com o Ollama, tudo fica no seu computador. Modelos menores usam menos memória, mas podem errar mais.";
  };
  providerSel.addEventListener("change", sync);
  $("input[name=temperature]", form).addEventListener("input", (e) => { $("#temp-out", form).textContent = e.target.value; });
  sync();

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const v = Object.fromEntries(new FormData(form).entries());
    const body = {
      provider: v.provider,
      model: v.model,
      temperature: Number(v.temperature),
      endpoint: v.endpoint || s.endpoint,
      base_url: v.base_url || "",
      api_key: v.api_key ? v.api_key : null,
      fallback_to_ollama: v.provider === "ollama" ? s.fallback_to_ollama : Boolean(v.fallback_to_ollama),
      default_exchange: v.default_exchange,
    };
    try {
      s = { ...s, ...(await api("/api/settings", { method: "PUT", body })) };
      toast("Ajustes salvos.");
      refreshStatus();
    } catch (err) {
      toast(err.message, "error");
    }
  });
}
