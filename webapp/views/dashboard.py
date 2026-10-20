"""Página Dashboard — visão geral e atalhos rápidos."""

import streamlit as st

from stonks_ai.utils.formatters import format_currency

from webapp.components.metrics import delta_vs_previous, previous_month_summary, render_metric


def page_dashboard(financial_agent, personal_finance_agent):
    from datetime import datetime as dt

    st.markdown('<div class="main-header">🚀 Stonks AI</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">'
        "Assistente financeiro inteligente — Ações B3/NYSE, Finanças Pessoais e IA Local"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Status do sistema ──
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric("Ações B3", "~400+", None)
    with col2:
        render_metric("Ações NYSE", "~6,000+", None)
    with col3:
        render_metric("Finanças Pessoais", "Ativo", None)
    with col4:
        llm_status = "Online" if financial_agent.check_llm_available() else "Offline"
        render_metric("IA Local", llm_status, None)

    # ── Resumo financeiro do mês atual ──
    st.markdown("---")
    st.markdown("### 💰 Resumo Financeiro do Mês")
    try:
        now = dt.now()
        dash_data = personal_finance_agent.get_dashboard(now.year, now.month)
        summary = dash_data["summary"]
        prev = previous_month_summary(now.year, now.month)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("💰 Receitas", format_currency(summary['total_income']),
                  delta=delta_vs_previous(summary['total_income'], prev, "total_income"))
        m2.metric("💸 Despesas", format_currency(summary['total_expense']),
                  delta=delta_vs_previous(summary['total_expense'], prev, "total_expense"),
                  delta_color="inverse")
        m3.metric("📊 Saldo", format_currency(summary['balance']),
                  delta=delta_vs_previous(summary['balance'], prev, "balance"))
        m4.metric("🔄 Transações", summary['transaction_count'])

        if summary['transaction_count'] == 0:
            st.info("👋 Nenhuma transação este mês. Vá para **Finanças Pessoais > Importar Extrato** para começar!")

    except Exception:
        st.caption("📊 Dados financeiros indisponíveis — inicialize com `stonks init`")

    st.markdown("---")

    # ── Atalhos rápidos ──
    st.markdown("### 🔥 Comece rápido")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**💲 Cotação**")
        ticker_quick = st.text_input(
            "Ticker", placeholder="Ex: PETR4, AAPL",
            key="dash_quote_ticker", label_visibility="collapsed",
        )
        if st.button("Ver Cotação", key="dash_quote_btn") and ticker_quick:
            st.session_state["page"] = "quote"
            st.session_state["quick_ticker"] = ticker_quick.upper()
            st.rerun()

    with col2:
        st.markdown("**🤖 Análise IA**")
        ticker_analyze = st.text_input(
            "Ticker", placeholder="Ex: VALE3, MSFT",
            key="dash_analyze_ticker", label_visibility="collapsed",
        )
        if st.button("Analisar", key="dash_analyze_btn") and ticker_analyze:
            st.session_state["page"] = "analyze"
            st.session_state["quick_ticker"] = ticker_analyze.upper()
            st.rerun()

    st.markdown("---")
    st.markdown("### 📋 Watchlist Rápida")
    from webapp.views.watchlist import _render_watchlist_table
    _render_watchlist_table(financial_agent, limit=5)
