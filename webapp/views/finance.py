"""Página Finanças Pessoais — dashboard, importação e transações."""

import os
import tempfile
from datetime import datetime

import pandas as pd
import streamlit as st


def page_finance(financial_agent, personal_finance_agent):
    st.markdown("## 💰 Finanças Pessoais")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard", "📥 Importar Extrato", "📝 Transações", "🏷️ Categorias",
    ])

    with tab1:
        _tab_dashboard(personal_finance_agent)

    with tab2:
        _tab_import(personal_finance_agent)

    with tab3:
        _tab_transactions(personal_finance_agent)

    with tab4:
        _tab_categories(personal_finance_agent)


def _tab_dashboard(personal_finance_agent):
    col1, col2 = st.columns(2)
    with col1:
        year = st.number_input("Ano", min_value=2020, max_value=2030, value=datetime.now().year)
    with col2:
        month = st.number_input("Mês", min_value=1, max_value=12, value=datetime.now().month)

    with st.spinner("Carregando dashboard..."):
        try:
            data = personal_finance_agent.get_dashboard(year, month)
            summary = data["summary"]

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 Receitas", f"R$ {summary['total_income']:,.2f}")
            m2.metric("💸 Despesas", f"R$ {summary['total_expense']:,.2f}")
            m3.metric("📊 Saldo", f"R$ {summary['balance']:,.2f}",
                      delta=f"R$ {summary['balance']:,.2f}")
            m4.metric("📈 Média/Dia", f"R$ {summary['avg_daily_expense']:,.2f}")

            if summary["top_categories"]:
                st.markdown("### 🏷️ Categorias com Mais Gastos")
                cat_df = pd.DataFrame(summary["top_categories"])
                st.dataframe(
                    cat_df[["name", "amount", "percent"]].rename(
                        columns={"name": "Categoria", "amount": "Valor (R$)", "percent": "%"}
                    ),
                    use_container_width=True, hide_index=True,
                )

            if data["active_goals"]:
                st.markdown("### 🎯 Metas Ativas")
                for g in data["active_goals"]:
                    pct = g.get("progress_percent", 0)
                    st.progress(min(pct / 100, 1.0))
                    st.caption(
                        f"{g['name']}: R$ {g['current_amount']:,.2f} / "
                        f"R$ {g['target_amount']:,.2f} ({pct:.1f}%)"
                    )

            if st.button("🤖 Gerar Resumo com IA"):
                with st.spinner("Gerando análise..."):
                    ai_text = personal_finance_agent.get_monthly_summary_ai(year, month)
                    st.info(ai_text)

        except Exception as e:
            st.error(f"Erro ao carregar dashboard: {e}")


def _tab_import(personal_finance_agent):
    st.markdown("### 📥 Importar Extrato Bancário")
    st.markdown("Formatos suportados: **CSV**, **Excel** (.xlsx/.xls), **PDF**")

    uploaded_file = st.file_uploader(
        "Selecione o arquivo de extrato",
        type=["csv", "xlsx", "xls", "pdf"],
    )

    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{uploaded_file.name}") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        with st.spinner("Importando transações..."):
            try:
                result = personal_finance_agent.import_file(tmp_path)

                if result["imported"] > 0:
                    st.success(f"✅ {result['imported']} transações importadas!")
                if result["duplicates"] > 0:
                    st.warning(f"⚠️ {result['duplicates']} duplicatas ignoradas")
                if result["errors"]:
                    for err in result["errors"]:
                        st.error(f"❌ {err}")
            except Exception as e:
                st.error(f"Erro na importação: {e}")

        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def _tab_transactions(personal_finance_agent):
    st.markdown("### 📝 Transações Recentes")

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filter_days = st.selectbox("Período", [7, 15, 30, 60, 90], index=1)
    with col_f2:
        filter_type = st.selectbox("Tipo", ["all", "expense", "income"])
    with col_f3:
        limit_n = st.number_input("Máximo", min_value=10, max_value=200, value=50)

    with st.spinner("Buscando transações..."):
        try:
            tx_type = None if filter_type == "all" else filter_type
            tx_list = personal_finance_agent.list_transactions(
                limit=limit_n, days=filter_days, transaction_type=tx_type
            )

            if tx_list:
                for tx in tx_list:
                    tx_id = tx["id"]
                    d = tx["date"]
                    d_str = d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else str(d)[:10]
                    tipo_icon = "💰" if tx["type"] == "income" else "💸"
                    valor_color = "var(--positive)" if tx["type"] == "income" else "var(--negative)"

                    with st.container(border=True):
                        cols = st.columns([3, 1, 1, 1])
                        with cols[0]:
                            st.markdown(
                                f"**{tx['description'][:60]}**  \n"
                                f"<span style='color: var(--text-muted); font-size: 0.85em;'>{d_str} · "
                                f"{tx.get('category_name') or 'Sem categoria'}</span>",
                                unsafe_allow_html=True,
                            )
                        with cols[1]:
                            st.markdown(
                                f"<span style='color: {valor_color}; "
                                f"font-weight: 700;'>{tipo_icon} R$ {tx['amount']:,.2f}</span>",
                                unsafe_allow_html=True,
                            )
                        with cols[2]:
                            if st.button("✏️", key=f"edit_{tx_id}", help="Editar transação"):
                                st.session_state["edit_tx_id"] = tx_id
                                st.session_state["edit_tx_data"] = tx
                                st.rerun()
                        with cols[3]:
                            if st.button("🗑️", key=f"del_{tx_id}", help="Remover transação"):
                                st.session_state["del_tx_id"] = tx_id
                                st.session_state["del_tx_desc"] = tx["description"][:60]
                                st.rerun()
            else:
                st.info("Nenhuma transação encontrada.")
        except Exception as e:
            st.error(f"Erro: {e}")

    # Diálogo de exclusão
    _render_delete_dialog(personal_finance_agent)
    # Formulário de edição
    _render_edit_form(personal_finance_agent)
    # Formulário de adição
    _render_add_form(personal_finance_agent)


def _render_delete_dialog(personal_finance_agent):
    if "del_tx_id" in st.session_state and st.session_state["del_tx_id"]:
        del_id = st.session_state["del_tx_id"]
        del_desc = st.session_state.get("del_tx_desc", "")
        st.markdown("---")
        st.warning(f"🗑️ **Confirmar exclusão** — {del_desc}")
        col_c1, col_c2, col_c3 = st.columns([1, 1, 2])
        with col_c1:
            if st.button("✅ Sim, excluir", type="primary", key="confirm_del"):
                with st.spinner("Excluindo..."):
                    try:
                        personal_finance_agent.delete_transaction(del_id)
                        st.success("✅ Transação excluída!")
                        st.session_state["del_tx_id"] = None
                        st.session_state["del_tx_desc"] = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao excluir: {e}")
        with col_c2:
            if st.button("❌ Cancelar", key="cancel_del"):
                st.session_state["del_tx_id"] = None
                st.session_state["del_tx_desc"] = None
                st.rerun()


def _render_edit_form(personal_finance_agent):
    if "edit_tx_id" in st.session_state and st.session_state["edit_tx_id"]:
        tx_data = st.session_state.get("edit_tx_data", {})
        st.markdown("---")
        st.markdown(f"### ✏️ Editando Transação #{st.session_state['edit_tx_id']}")

        with st.form("edit_transaction"):
            edit_desc = st.text_input("Descrição", value=tx_data.get("description", ""))
            edit_amount = st.number_input(
                "Valor", min_value=0.01, format="%.2f",
                value=float(tx_data.get("amount", 0)),
            )
            edit_type = st.selectbox(
                "Tipo", ["expense", "income"],
                index=0 if tx_data.get("type") == "expense" else 1,
            )

            cat_options = []
            try:
                cats = personal_finance_agent.list_categories()
                cat_options = [c["name"] for c in cats]
            except Exception:
                pass
            current_cat = tx_data.get("category_name", "")
            cat_index = 0
            if current_cat in cat_options:
                cat_index = cat_options.index(current_cat) + 1
            edit_cat = st.selectbox("Categoria", [""] + cat_options, index=cat_index)

            raw_date = tx_data.get("date", "")
            if hasattr(raw_date, "strftime"):
                default_date_str = raw_date.strftime("%Y-%m-%d")
            else:
                default_date_str = str(raw_date)[:10] if raw_date else ""
            edit_date = st.date_input(
                "Data",
                value=datetime.strptime(default_date_str, "%Y-%m-%d") if default_date_str else datetime.now(),
            )
            edit_notes = st.text_area("Observações", value=tx_data.get("notes") or "")

            col_s1, col_s2, col_s3 = st.columns([1, 1, 2])
            with col_s1:
                submitted = st.form_submit_button("💾 Salvar", type="primary")
            with col_s2:
                cancelled = st.form_submit_button("❌ Cancelar")

            if submitted:
                with st.spinner("Salvando..."):
                    try:
                        updated = personal_finance_agent.update_transaction(
                            transaction_id=st.session_state["edit_tx_id"],
                            description=edit_desc.strip(),
                            amount=edit_amount,
                            tx_type=edit_type,
                            category_name=edit_cat or None,
                            date=edit_date.strftime("%Y-%m-%d"),
                            notes=edit_notes.strip() or None,
                        )
                        if updated:
                            st.success("✅ Transação atualizada!")
                        else:
                            st.error("❌ Transação não encontrada.")
                        st.session_state["edit_tx_id"] = None
                        st.session_state["edit_tx_data"] = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

            if cancelled:
                st.session_state["edit_tx_id"] = None
                st.session_state["edit_tx_data"] = None
                st.rerun()


def _render_add_form(personal_finance_agent):
    with st.expander("➕ Adicionar Transação Manual"):
        with st.form("add_transaction"):
            desc = st.text_input("Descrição")
            amount = st.number_input("Valor", min_value=0.01, format="%.2f")
            tx_type_sel = st.selectbox("Tipo", ["expense", "income"])
            cat_options = []
            try:
                cats = personal_finance_agent.list_categories()
                cat_options = [c["name"] for c in cats]
            except Exception:
                pass
            cat_sel = st.selectbox("Categoria", [""] + cat_options)
            notes = st.text_area("Observações (opcional)")

            if st.form_submit_button("Adicionar"):
                with st.spinner("Adicionando..."):
                    try:
                        tx = personal_finance_agent.add_transaction(
                            description=desc,
                            amount=amount,
                            tx_type=tx_type_sel,
                            category_name=cat_sel or None,
                            notes=notes or None,
                        )
                        st.success(f"✅ Transação adicionada: {tx['description']}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")


def _tab_categories(personal_finance_agent):
    st.markdown("### 🏷️ Categorias")
    with st.spinner("Carregando categorias..."):
        try:
            cats = personal_finance_agent.list_categories()
            if cats:
                rows = []
                for c in cats:
                    limit_str = (
                        f"R$ {c['budget_limit'] / 100:,.2f}"
                        if c.get("budget_limit") else "-"
                    )
                    rows.append({
                        "ID": c["id"],
                        "Ícone": c.get("icon", "📦"),
                        "Nome": c["name"],
                        "Limite": limit_str,
                    })
                st.dataframe(rows, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma categoria cadastrada.")
        except Exception as e:
            st.error(f"Erro: {e}")
