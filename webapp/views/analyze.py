"""Página Análise IA — análise completa de ações com inteligência artificial."""

import streamlit as st

from stonks_ai.collectors.stocks.base import StockCollectorError
from stonks_ai.utils.formatters import format_change, format_currency, format_large_number, format_percent, format_ticker_display
from webapp.components.metrics import render_metric


def page_analyze(financial_agent, personal_finance_agent):
    st.markdown('<div class="main-header">🤖 Análise IA</div>', unsafe_allow_html=True)

    ticker = st.text_input(
        "Ticker da ação", placeholder="Ex: PETR4, VALE3, AAPL, MSFT",
        value=st.session_state.get("quick_ticker", ""), key="analyze_ticker_input",
    )
    exchange = st.selectbox("Bolsa", ["Auto", "B3", "NYSE"], index=0, key="analyze_exchange")

    if st.button("🔍 Analisar com IA", type="primary") and ticker:
        st.session_state["quick_ticker"] = ""
        with st.spinner(f"🤖 Coletando dados e gerando análise para {ticker.upper()}..."):
            try:
                exch = None if exchange == "Auto" else exchange
                result = financial_agent.analyze(ticker.upper(), exch)

                q = result["quote"]
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
                    render_metric("Empresa", q.name or "N/A")
                with col4:
                    render_metric("Bolsa", q.exchange)

                fund = result.get("fundamentals")
                if fund:
                    st.markdown("### 📊 Fundamentos")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        render_metric("Setor", fund.sector or "N/A")
                    with col2:
                        render_metric("Market Cap", format_large_number(fund.market_cap))
                    with col3:
                        render_metric("P/L", f"{fund.pe_ratio:.2f}" if fund.pe_ratio else "N/A")
                    with col4:
                        render_metric(
                            "Dividend Yield",
                            format_percent(fund.dividend_yield) if fund.dividend_yield else "N/A",
                        )

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        render_metric("ROE", format_percent(fund.roe) if fund.roe else "N/A")
                    with col2:
                        render_metric("P/VP", f"{fund.pb_ratio:.2f}" if fund.pb_ratio else "N/A")
                    with col3:
                        render_metric("Beta", f"{fund.beta:.2f}" if fund.beta else "N/A")
                    with col4:
                        render_metric("Margem Líquida", format_percent(fund.net_margin) if fund.net_margin else "N/A")

                analysis = result.get("analysis", "")
                if analysis and "não disponível" not in analysis.lower():
                    st.markdown("### 🤖 Análise da Inteligência Artificial")
                    st.markdown(
                        f'<div style="background: var(--ai-box-bg); border-radius: 10px; '
                        f'padding: 1.5rem; border: 1px solid var(--ai-box-border); '
                        f'line-height: 1.7;">{analysis}</div>',
                        unsafe_allow_html=True,
                    )
                elif analysis:
                    st.warning(f"⚠️ {analysis}")

            except StockCollectorError as e:
                st.error(f"❌ {e}")
            except Exception as e:
                st.error(f"Erro inesperado: {e}")
