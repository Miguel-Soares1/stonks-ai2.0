"""Página Histórico — gráfico interativo de preços."""

import pandas as pd
import streamlit as st

from stonks_ai.collectors.stocks.base import StockCollectorError
from stonks_ai.utils.formatters import format_change, format_large_number
from webapp.components.charts import build_price_chart
from webapp.components.metrics import render_metric


def page_history(financial_agent, personal_finance_agent):
    st.markdown('<div class="main-header">📈 Histórico</div>', unsafe_allow_html=True)

    ticker = st.text_input(
        "Ticker da ação", placeholder="Ex: PETR4, AAPL",
        value=st.session_state.get("quick_ticker", ""), key="history_ticker_input",
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        exchange = st.selectbox("Bolsa", ["Auto", "B3", "NYSE"], index=0, key="history_exchange")
    with col2:
        period = st.selectbox(
            "Período", ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
            index=2, key="history_period",
        )
    with col3:
        interval = st.selectbox(
            "Intervalo", ["1d", "1h", "5m", "15m", "30m", "60m"],
            index=0, key="history_interval",
        )

    if st.button("📊 Gerar Gráfico", type="primary") and ticker:
        st.session_state["quick_ticker"] = ""
        with st.spinner(f"Buscando histórico de {ticker.upper()}..."):
            try:
                exch = None if exchange == "Auto" else exchange
                h = financial_agent.get_history(ticker.upper(), exch, period=period, interval=interval)

                if not h.data:
                    st.warning(f"⚠️ Nenhum dado histórico para {ticker} no período {period}.")
                    return

                first = h.data[0]
                last = h.data[-1]
                change_val = last["close"] - first["close"]
                change_pct = (change_val / first["close"] * 100) if first["close"] else 0

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    render_metric("Período", f"{first['date'][:10]} → {last['date'][:10]}")
                with col2:
                    render_metric("Variação", format_change(change_val, change_pct), change_pct)
                with col3:
                    avg_price = sum(d["close"] for d in h.data) / len(h.data)
                    render_metric("Média", f"{avg_price:.2f}")
                with col4:
                    render_metric("Fechamento Atual", f"{last['close']:.2f}", change_pct)

                fig = build_price_chart(h.data, ticker.upper(), title=f"{ticker.upper()} - {period}")
                st.plotly_chart(fig, use_container_width=True)

                st.markdown("### 📋 Últimos pregões")
                df_display = pd.DataFrame(h.data[-20:])
                df_display["date"] = pd.to_datetime(df_display["date"]).dt.strftime("%Y-%m-%d")
                df_display = df_display.rename(columns={
                    "date": "Data", "open": "Abertura", "high": "Máxima",
                    "low": "Mínima", "close": "Fechamento", "volume": "Volume",
                })
                df_display["Volume"] = df_display["Volume"].apply(lambda x: format_large_number(x))
                st.dataframe(df_display, use_container_width=True, hide_index=True)

            except StockCollectorError as e:
                st.error(f"❌ {e}")
            except Exception as e:
                st.error(f"Erro inesperado: {e}")
