"""Página Watchlist — gestão da lista de ativos monitorados."""

import pandas as pd
import streamlit as st

from stonks_ai.collectors.stocks.base import StockCollectorError
from stonks_ai.database import DatabaseError, db
from stonks_ai.models.watchlist import WatchlistItem
from stonks_ai.utils.formatters import format_currency


def _render_watchlist_table(financial_agent, limit=None):
    """Renderiza a tabela da watchlist (reutilizável entre dashboard e watchlist)."""
    try:
        rows = []
        with db.session() as session:
            query = session.query(WatchlistItem).order_by(WatchlistItem.added_at.desc())
            if limit:
                query = query.limit(limit)
            items = query.all()

            if not items:
                st.info("📋 Watchlist vazia. Adicione tickers usando o formulário abaixo.")
                return

            for item in items:
                try:
                    q = financial_agent.get_quote(item.ticker, item.exchange)
                    rows.append({
                        "Ticker": q.ticker,
                        "Bolsa": item.exchange,
                        "Preço": format_currency(q.price, q.currency),
                        "Variação": f"{q.change_percent:+.2f}%",
                        "Alvo": (
                            format_currency(item.target_price, q.currency)
                            if item.target_price else "-"
                        ),
                    })
                except StockCollectorError:
                    rows.append({
                        "Ticker": item.ticker, "Bolsa": item.exchange,
                        "Preço": "Erro", "Variação": "-", "Alvo": "-",
                    })

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    except DatabaseError as e:
        st.error(f"❌ Erro no banco: {e}")
    except Exception as e:
        st.error(f"❌ Erro: {e}")


def page_watchlist(financial_agent, personal_finance_agent):
    st.markdown('<div class="main-header">📋 Watchlist</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 Minha Watchlist", "➕ Adicionar / ❌ Remover"])

    with tab1:
        _render_watchlist_table(financial_agent)

    with tab2:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### ➕ Adicionar Ticker")
            add_ticker = st.text_input("Ticker", placeholder="Ex: PETR4", key="wl_add_ticker")
            add_exchange = st.selectbox("Bolsa", ["B3", "NYSE"], index=0, key="wl_add_exchange")
            add_name = st.text_input("Nome da watchlist", value="Minha Watchlist", key="wl_add_name")
            add_target = st.number_input("Preço alvo (opcional)", min_value=0.0, step=0.01, key="wl_add_target")

            if st.button("✅ Adicionar", type="primary") and add_ticker:
                try:
                    with db.session() as session:
                        item = WatchlistItem(
                            name=add_name,
                            ticker=add_ticker.upper(),
                            exchange=add_exchange.upper(),
                            target_price=add_target if add_target > 0 else None,
                        )
                        session.add(item)
                    st.success(f"✅ {add_ticker.upper()} adicionado à watchlist!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro: {e}")

        with col2:
            st.markdown("### ❌ Remover Ticker")
            try:
                ticker_options = {}
                with db.session() as session:
                    items = session.query(WatchlistItem).all()
                    if items:
                        ticker_options = {
                            f"{item.ticker} ({item.exchange})": item.id
                            for item in items
                        }

                if ticker_options:
                    to_remove = st.selectbox(
                        "Selecione para remover",
                        list(ticker_options.keys()),
                        key="wl_remove_select",
                    )

                    if st.button("🗑️ Remover", type="secondary") and to_remove:
                        item_id = ticker_options[to_remove]
                        with db.session() as session:
                            item = session.query(WatchlistItem).get(item_id)
                            if item:
                                session.delete(item)
                        st.success(f"✅ {to_remove} removido da watchlist!")
                        st.rerun()
                else:
                    st.info("Watchlist vazia. Adicione tickers primeiro.")
            except Exception as e:
                st.error(f"❌ Erro: {e}")
