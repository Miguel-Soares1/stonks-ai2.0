"""Página Cotação — preço atual de uma ação."""

import streamlit as st

from stonks_ai.collectors.stocks.base import StockCollectorError
from stonks_ai.utils.formatters import format_change, format_currency, format_large_number, format_ticker_display
from webapp.components.metrics import render_info_box, render_metric


def page_quote(financial_agent, personal_finance_agent):
    st.markdown('<div class="main-header">💲 Cotação</div>', unsafe_allow_html=True)

    ticker = st.text_input(
        "Ticker da ação", placeholder="Ex: PETR4, VALE3, AAPL, MSFT",
        value=st.session_state.get("quick_ticker", ""), key="quote_ticker_input",
    )
    exchange = st.selectbox(
        "Bolsa (deixe Auto para detecção automática)",
        ["Auto", "B3", "NYSE"], index=0, key="quote_exchange",
    )

    if st.button("🔍 Buscar Cotação", type="primary") and ticker:
        st.session_state["quick_ticker"] = ""
        with st.spinner(f"Buscando cotação de {ticker.upper()}..."):
            try:
                exch = None if exchange == "Auto" else exchange
                q = financial_agent.get_quote(ticker.upper(), exch)

                st.markdown(
                    f'<h2 style="color: var(--accent-primary);">'
                    f"{format_ticker_display(q.ticker, q.exchange)}</h2>",
                    unsafe_allow_html=True,
                )

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    render_metric("Preço", format_currency(q.price, q.currency), q.change_percent)
                with col2:
                    render_metric("Variação", format_change(q.change, q.change_percent), q.change_percent)
                with col3:
                    render_metric("Máxima", format_currency(q.high, q.currency))
                with col4:
                    render_metric("Mínima", format_currency(q.low, q.currency))

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    render_metric("Abertura", format_currency(q.open_price, q.currency))
                with col2:
                    render_metric("Fech. Ant.", format_currency(q.previous_close, q.currency))
                with col3:
                    render_metric("Volume", format_large_number(q.volume))
                with col4:
                    render_metric("Empresa", q.name or "N/A")

                st.markdown("---")
                render_info_box(
                    "📌 Dica",
                    f"Use o menu **Histórico** para ver o gráfico de {q.ticker}, "
                    f"ou **Análise IA** para uma análise completa com inteligência artificial.",
                )

            except StockCollectorError as e:
                st.error(f"❌ {e}")
            except Exception as e:
                st.error(f"Erro inesperado: {e}")
