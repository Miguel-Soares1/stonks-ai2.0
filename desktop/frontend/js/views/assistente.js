// Assistente: conversa com a IA em tela cheia (a mesma conversa do painel flutuante).

import { $ } from "../core.js";
import { mountChat, newChat } from "../chat.js";

export async function render(root) {
  root.innerHTML = `
    <div class="page-head">
      <h1 class="page-title">Conversar com a IA</h1>
      <button class="btn" type="button" id="new-chat">Nova conversa</button>
    </div>
    <div id="chat-host"></div>`;
  const chat = mountChat($("#chat-host", root));
  $("#new-chat", root).addEventListener("click", () => { newChat(); chat.focus(); });
  chat.focus();
}
