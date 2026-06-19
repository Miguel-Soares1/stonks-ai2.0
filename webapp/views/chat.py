"""Página Chat Financeiro — conversa com IA sobre investimentos."""

import streamlit as st


def page_chat(financial_agent, personal_finance_agent):
    st.markdown('<div class="main-header">💬 Chat Financeiro</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">'
        "Tire dúvidas sobre mercado financeiro, investimentos, "
        "indicadores, economia e mais"
        "</div>",
        unsafe_allow_html=True,
    )

    # Inicializa histórico da conversa
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
        st.session_state["chat_history"].append({
            "role": "assistant",
            "content": (
                "Olá! 👋 Sou o assistente financeiro do **Stonks AI**. "
                "Pode me perguntar sobre:\n\n"
                "• 📊 **Ações e mercado** — B3, NYSE, ETFs, FIIs\n"
                "• 📈 **Indicadores** — P/L, P/VP, ROE, Dividend Yield\n"
                "• 💰 **Estratégias** — Value investing, growth, dividendos\n"
                "• 🏦 **Economia** — Juros, inflação, câmbio, PIB\n"
                "• 📝 **Finanças pessoais** — Orçamento, reserva, planejamento\n\n"
                "**Como posso ajudar você hoje?** 🚀"
            ),
        })

    # Sugestões rápidas (só no início da conversa)
    user_msgs = [m for m in st.session_state["chat_history"] if m["role"] == "user"]
    if not user_msgs:
        st.markdown("### ⚡ Perguntas rápidas")
        quick_questions = [
            "O que é P/L e como interpretar?",
            "Qual a diferença entre CDB e Tesouro Direto?",
            "Como calcular dividend yield?",
            "O que é value investing?",
            "Como declarar ações no Imposto de Renda?",
            "O que é um ETF e como investir?",
        ]
        cols = st.columns(2)
        for i, question in enumerate(quick_questions):
            col = cols[i % 2]
            with col:
                if st.button(question, key=f"quick_q_{i}", use_container_width=True):
                    _handle_chat_message(financial_agent, question)

    # Exibe histórico
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input do utilizador
    if prompt := st.chat_input("Digite sua dúvida financeira...", key="chat_input"):
        _handle_chat_message(financial_agent, prompt)

    # Botão para limpar conversa
    if st.session_state["chat_history"]:
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🗑️ Limpar Conversa", use_container_width=True):
                st.session_state["chat_history"] = []
                st.rerun()


def _handle_chat_message(financial_agent, message: str):
    """Processa uma mensagem do chat e adiciona ao histórico."""
    st.session_state["chat_history"].append({"role": "user", "content": message})

    # Prepara histórico para contexto (últimas 10 mensagens)
    history_for_context = st.session_state["chat_history"][-10:]

    try:
        response = financial_agent.chat(
            message=message,
            conversation_history=[
                {"role": m["role"], "content": m["content"]}
                for m in history_for_context
                if m["role"] != "assistant" or m is not history_for_context[-1]
            ],
        )
        st.session_state["chat_history"].append({"role": "assistant", "content": response})
    except Exception as e:
        st.session_state["chat_history"].append({
            "role": "assistant",
            "content": f"❌ **Erro ao processar sua pergunta:** {e}",
        })

    st.rerun()
