"""Página Comparar — comparação de múltiplas ações lado a lado."""

import pandas as pd
import streamlit as st

from stonks_ai.utils.formatters import format_currency, format_percent
from stonks_ai.utils.validators import detect_exchange
from webapp.components.charts import build_comparison_chart


def page_compare(financial_agent, personal_finance_agent):
    st.markdown('<div class="main-header">⚖️ Comparar Ações</div>', unsafe_allow_html=True)

    tickers_str = st.text_input(
        "Tickers separados por vírgula",
        placeholder="Ex: PETR4, VALE3, ITUB4, BBDC4",
        key="compare_tickers_input",
    )

    col1, col2 = st.columns(2)
    with col1:
        period = st.selectbox(
            "Período para gráfico",
            ["1mo", "3mo", "6mo", "1y", "2y"],
            index=2, key="compare_period",
        )

    if st.button("⚖️ Comparar", type="primary") and tickers_str:
        tickers = [t.strip().upper() for t in tickers_str.split(",") if t.strip()]

        if len(tickers) < 2:
            st.error("❌ Informe pelo menos 2 tickers para comparar.")
            return

        with st.spinner(f"Comparando {', '.join(tickers)}..."):
            try:
                result = financial_agent.compare(tickers)

                st.markdown("### 📊 Tabela Comparativa")
                rows = []
                for q, f in zip(result["quotes"], result["fundamentals"]):
                    rows.append({
                        "Ticker": q.ticker,
                        "Bolsa": q.exchange,
                        "Preço": format_currency(q.price, q.currency),
                        "Variação": f"{q.change_percent:+.2f}%",
                        "P/L": f"{f.pe_ratio:.2f}" if f and f.pe_ratio else "N/A",
                        "DY": format_percent(f.dividend_yield) if f and f.dividend_yield else "N/A",
                    })

                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                # Gráfico comparativo
                st.markdown("### 📈 Performance Relativa (Base 100)")
                datasets = {}
                for ticker in tickers:
                    try:
                        exch = detect_exchange(ticker)
                        h = financial_agent.get_history(ticker, exch, period=period)
                        if h.data:
                            df = pd.DataFrame(h.data)
                            df["date"] = pd.to_datetime(df["date"])
                            datasets[ticker] = df
                    except Exception:
                        pass

                if datasets:
                    fig = build_comparison_chart(datasets)
                    st.plotly_chart(fig, use_container_width=True)

                analysis = result.get("analysis", "")
                if analysis and "não disponível" not in analysis.lower():
                    st.markdown("### 🤖 Análise Comparativa IA")
                    st.markdown(
                        f'<div style="background: var(--ai-box-bg); border-radius: 10px; '
                        f'padding: 1.5rem; border: 1px solid var(--ai-box-border); '
                        f'line-height: 1.7;">{analysis}</div>',
                        unsafe_allow_html=True,
                    )

            except Exception as e:
                st.error(f"❌ Erro: {e}")
