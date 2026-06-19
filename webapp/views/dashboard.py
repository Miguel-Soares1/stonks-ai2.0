"""Página Dashboard — visão geral e atalhos rápidos."""

import streamlit as st

from webapp.components.metrics import render_metric


def page_dashboard(financial_agent, personal_finance_agent):
    st.markdown('<div class="main-header">🚀 Stonks AI</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">'
        "Assistente financeiro inteligente — Ações B3/NYSE, Finanças Pessoais e IA Local"
        "</div>",
        unsafe_allow_html=True,
    )

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
