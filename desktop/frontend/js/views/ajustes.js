// Ajustes: qual IA usar (local ou remota), bloqueio por PIN, backup e informações do sistema.

import { api, confirmDialog, esc, formDialog, icon, toast, $ } from "../core.js";

const REASONS = { manual: "Manual", auto: "Automático", antes: "Antes de restaurar" };

const sizeText = (bytes) => bytes < 1024 * 1024
  ? `${Math.max(1, Math.round(bytes / 1024))} KB`
  : `${(bytes / 1024 / 1024).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} MB`;

const whenText = (iso) => new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(iso));

function setupBackups(root) {
  const list = $("#backup-list", root);

  const load = async () => {
    try {
      const { items } = await api("/api/backups");
      if (!items.length) {
        list.innerHTML = `<p class="empty">Nenhum backup ainda. O primeiro automático é criado ao abrir o app.</p>`;
        return;
      }
      list.innerHTML = `<table class="table">
        <thead><tr><th>Data</th><th>Tipo</th><th class="num">Tamanho</th><th class="actions"><span class="sr-only">Ações</span></th></tr></thead>
        <tbody>${items.map((b) => `<tr data-name="${esc(b.name)}">
          <td class="nowrap">${whenText(b.created_at)}</td>
          <td>${esc(REASONS[b.reason] || b.reason)}</td>
          <td class="num">${sizeText(b.size_bytes)}</td>
          <td class="actions"><button class="btn" type="button" data-restore>Restaurar</button></td>
        </tr>`).join("")}</tbody></table>`;
      list.querySelectorAll("[data-restore]").forEach((b) => b.addEventListener("click", () => {
        const row = b.closest("tr");
        restore(`/api/backups/${encodeURIComponent(row.dataset.name)}/restore`, undefined,
          `de ${row.cells[0].textContent}`);
      }));
    } catch (e) {
      list.innerHTML = `<p class="empty">${esc(e.message)}</p>`;
    }
  };

  // Restaurar troca todos os dados; o estado atual é salvo antes para poder voltar
  const restore = async (path, raw, label) => {
    const ok = await confirmDialog({
      title: "Restaurar este backup?",
      message: `Os dados atuais serão substituídos pelos do backup ${label}. Antes disso, o app salva uma cópia de como está agora, para você poder voltar.`,
      confirmLabel: "Restaurar",
    });
    if (!ok) return;
    try {
      await api(path, { method: "POST", raw });
      toast("Backup restaurado. Recarregando…");
      setTimeout(() => location.reload(), 900);
    } catch (e) {
      toast(`Não foi possível restaurar: ${e.message}`, "error");
    }
  };

  const nowBtn = $("#backup-now", root);
  nowBtn.addEventListener("click", async () => {
    nowBtn.disabled = true;
    try {
      await api("/api/backups", { method: "POST" });
      toast("Backup criado.");
      load();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      nowBtn.disabled = false;
    }
  });
  $("#backup-folder", root).addEventListener("click", () =>
    api("/api/backups/open-folder", { method: "POST" }).catch((err) => toast(err.message, "error")));
  $("#restore-input", root).addEventListener("change", (e) => {
    const file = e.target.files[0];
    e.target.value = "";
    if (file) restore("/api/backups/restore-file", file, `"${file.name}"`);
  });
  load();
}

const PROVIDERS = [
  ["ollama", "Ollama (no seu computador)"],
  ["deepseek", "DeepSeek (nuvem)"],
  ["openai", "OpenAI (nuvem)"],
  ["openai_compatible", "Outro compatível com OpenAI (nuvem)"],
];

const TIMEOUTS = [[0, "Só ao abrir o app"], [5, "Após 5 minutos sem uso"], [10, "Após 10 minutos sem uso"],
  [30, "Após 30 minutos sem uso"], [60, "Após 1 hora sem uso"]];

// Bandeja do Windows: o app continua rodando com a janela fechada, para os alertas de preço-alvo
function setupBackground(panel) {
  const paint = (b) => {
    panel.innerHTML = `
      <h2>Segundo plano</h2>
      <div class="form-grid">
        <label class="check"><input type="checkbox" name="close_to_tray" ${b.close_to_tray ? "checked" : ""}>
          Ao fechar a janela, continuar na bandeja do Windows (perto do relógio)</label>
        <label class="check"><input type="checkbox" name="start_with_windows" ${b.start_with_windows ? "checked" : ""} ${b.autostart_supported ? "" : "disabled"}>
          Abrir com o Windows, já na bandeja</label>
      </div>
      <p class="muted small">Na bandeja, o app avisa com uma notificação quando um ativo da watchlist chega ao preço-alvo
        (verifica a cada 5 minutos no horário de pregão). Para fechar de vez, clique no ícone com o botão direito e escolha Sair.
        ${b.autostart_supported ? "" : "Abrir com o Windows só funciona no app instalado."}</p>`;
    panel.querySelectorAll("input[type=checkbox]").forEach((el) => el.addEventListener("change", async () => {
      const body = {
        close_to_tray: $("input[name=close_to_tray]", panel).checked,
        start_with_windows: $("input[name=start_with_windows]", panel).checked,
      };
      try { paint(await api("/api/settings/background", { method: "PUT", body })); toast("Ajuste salvo."); }
      catch (e) { toast(e.message, "error"); paint(b); }
    }));
  };
  api("/api/settings/background").then(paint).catch((e) => { panel.innerHTML = `<p class="empty">${esc(e.message)}</p>`; });
}

function setupLock(panel, applyLockStatus) {
  const paint = (st) => {
    applyLockStatus(st);
    panel.innerHTML = `
      <div class="panel-head"><h2>Bloqueio por PIN</h2>
        <div class="toolbar">${st.enabled
          ? `<button class="btn" type="button" data-pin="remove">Remover PIN</button>
             <button class="btn btn-primary" type="button" data-pin="change">Trocar PIN</button>`
          : `<button class="btn btn-primary" type="button" data-pin="set">${icon("lock")}<span>Definir PIN</span></button>`}
        </div>
      </div>
      <p class="muted small">${st.enabled
        ? "O app pede o PIN ao abrir e depois de um tempo sem uso. Use o cadeado no topo para bloquear na hora."
        : "Sem PIN, qualquer pessoa que usar este computador consegue abrir o app e ver suas finanças."}
        O PIN protege o app aberto, mas não criptografa os arquivos: quem entra na sua conta do Windows ainda acessa a pasta de dados.</p>
      ${st.enabled ? `<label class="field narrow"><span>Bloquear de novo</span><select name="lock-timeout">${TIMEOUTS.map(([v, l]) =>
        `<option value="${v}" ${v === st.timeout_minutes ? "selected" : ""}>${l}</option>`).join("")}</select></label>` : ""}`;

    panel.querySelectorAll("[data-pin]").forEach((b) => b.addEventListener("click", () => editPin(b.dataset.pin)));
    const sel = $("select[name=lock-timeout]", panel);
    if (sel) sel.addEventListener("change", async () => {
      try { paint(await api("/api/lock/timeout", { method: "PUT", body: { minutes: Number(sel.value) } })); toast("Tempo de bloqueio salvo."); }
      catch (e) { toast(e.message, "error"); }
    });
  };

  const pinField = (name, label, autofocus) => ({ name, label, type: "password", required: true, autofocus,
    placeholder: "4 a 8 números" });
  const editPin = async (mode) => {
    const fields = {
      set: [pinField("new_pin", "Novo PIN", true), pinField("confirm", "Repita o PIN")],
      change: [pinField("current_pin", "PIN atual", true), pinField("new_pin", "Novo PIN"), pinField("confirm", "Repita o novo PIN")],
      remove: [pinField("current_pin", "PIN atual", true)],
    }[mode];
    const st = await formDialog({
      title: { set: "Definir PIN", change: "Trocar PIN", remove: "Remover PIN" }[mode],
      submitLabel: { set: "Definir PIN", change: "Trocar PIN", remove: "Remover PIN" }[mode],
      fields,
      onSubmit: (v) => {
        if (mode !== "remove" && v.new_pin !== v.confirm) throw new Error("Os dois PINs não são iguais.");
        return api("/api/lock/pin", { method: "PUT", body: { new_pin: mode === "remove" ? "" : v.new_pin, current_pin: v.current_pin || "" } });
      },
    });
    if (st) {
      toast({ set: "PIN definido.", change: "PIN trocado.", remove: "PIN removido." }[mode]);
      paint(st);
    }
  };

  api("/api/lock").then(paint).catch((e) => { panel.innerHTML = `<p class="empty">${esc(e.message)}</p>`; });
}

export async function render(root, _params, { refreshStatus, applyLockStatus }) {
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
    <article class="panel" id="lock-panel"></article>
    <article class="panel" id="background-panel"></article>
    <article class="panel">
      <div class="panel-head"><h2>Backup</h2>
        <div class="toolbar">
          <button class="btn" type="button" id="backup-folder">Abrir pasta</button>
          <label class="btn" for="restore-input">${icon("upload")}<span>Restaurar de um arquivo</span></label>
          <input id="restore-input" type="file" accept=".db" hidden>
          <button class="btn btn-primary" type="button" id="backup-now">Fazer backup agora</button>
        </div>
      </div>
      <p class="muted small">O app faz uma cópia automática por semana e guarda as 8 mais recentes. Para se proteger
        de perder o computador, copie a pasta de backups para um pendrive ou para a nuvem.</p>
      <div id="backup-list"><p class="empty">Carregando…</p></div>
    </article>
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

  setupLock($("#lock-panel", root), applyLockStatus);
  setupBackground($("#background-panel", root));
  setupBackups(root);

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
