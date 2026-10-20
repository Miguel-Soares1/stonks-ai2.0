"""Página Finanças Pessoais — dashboard, importação e transações."""

import os
import tempfile
from datetime import datetime

import streamlit as st

from stonks_ai.utils.formatters import format_currency
from webapp.components.metrics import delta_vs_previous, previous_month_summary


def page_finance(financial_agent, personal_finance_agent):
    st.markdown("## 💰 Finanças Pessoais")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Dashboard", "📥 Importar Extrato", "📝 Transações",
        "🏷️ Categorias", "💰 Orçamento", "🏦 Contas",
    ])

    with tab1:
        _tab_dashboard(personal_finance_agent)

    with tab2:
        _tab_import(personal_finance_agent)

    with tab3:
        _tab_transactions(personal_finance_agent)

    with tab4:
        _tab_categories(personal_finance_agent)

    with tab5:
        _tab_budget(personal_finance_agent)

    with tab6:
        _tab_accounts(personal_finance_agent)


def _tab_dashboard(personal_finance_agent):
    from webapp.components.charts import (
        build_balance_line_chart,
        build_category_pie_chart,
        build_monthly_bars_chart,
    )

    col1, col2 = st.columns(2)
    with col1:
        year = st.number_input("Ano", min_value=2020, max_value=2030, value=datetime.now().year)
    with col2:
        month = st.number_input("Mês", min_value=1, max_value=12, value=datetime.now().month)

    with st.spinner("Carregando dashboard..."):
        try:
            data = personal_finance_agent.get_dashboard(year, month)
            summary = data["summary"]

            # ── Métricas rápidas ──
            prev = previous_month_summary(year, month)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 Receitas", format_currency(summary['total_income']),
                      delta=delta_vs_previous(summary['total_income'], prev, "total_income"))
            m2.metric("💸 Despesas", format_currency(summary['total_expense']),
                      delta=delta_vs_previous(summary['total_expense'], prev, "total_expense"),
                      delta_color="inverse")
            m3.metric("📊 Saldo", format_currency(summary['balance']),
                      delta=delta_vs_previous(summary['balance'], prev, "balance"))
            m4.metric("📈 Média/Dia", format_currency(summary['avg_daily_expense']))

            st.markdown("---")

            # ── Dados para gráficos ──
            chart_data = personal_finance_agent.get_multi_month_dashboard(months=6)

            # ── Linha 1: Pizza (categorias) + Barras (receitas vs despesas) ──
            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                if summary["top_categories"]:
                    pie_fig = build_category_pie_chart(
                        summary["top_categories"],
                        title=f"Gastos por Categoria — {month:02d}/{year}",
                    )
                    st.plotly_chart(pie_fig, width='stretch')
                else:
                    st.info("📊 Sem dados de categorias para exibir gráfico de pizza.")

            with col_chart2:
                monthly = chart_data.get("monthly_summaries", [])
                if monthly:
                    bar_fig = build_monthly_bars_chart(monthly)
                    st.plotly_chart(bar_fig, width='stretch')
                else:
                    st.info("📊 Sem dados históricos para exibir gráfico de barras.")

            # ── Linha 2: Evolução do saldo (largura total) ──
            balance_hist = chart_data.get("balance_history", [])
            if balance_hist:
                line_fig = build_balance_line_chart(balance_hist)
                st.plotly_chart(line_fig, width='stretch')
            else:
                st.info("📊 Sem dados de saldo para exibir gráfico de evolução.")

            st.markdown("---")

            # ── Metas ativas ──
            if data["active_goals"]:
                st.markdown("### 🎯 Metas Ativas")
                goal_cols = st.columns(min(len(data["active_goals"]), 3))
                for i, g in enumerate(data["active_goals"]):
                    pct = g.get("progress_percent", 0)
                    with goal_cols[i % 3]:
                        with st.container(border=True):
                            icon = g.get("icon", "🎯")
                            st.markdown(f"**{icon} {g['name']}**")
                            st.progress(min(pct / 100, 1.0))
                            st.caption(
                                f"{format_currency(g['current_amount'])} / "
                                f"{format_currency(g['target_amount'])} ({pct:.1f}%)"
                            )
                            if g.get("deadline"):
                                d = g["deadline"]
                                d_str = d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else str(d)[:10]
                                st.caption(f"📅 Prazo: {d_str}")

            # ── Resumo com IA ──
            if st.button("🤖 Gerar Resumo com IA", width='stretch'):
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

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        filter_days = st.selectbox("Período", [7, 15, 30, 60, 90], index=1)
    with col_f2:
        filter_type = st.selectbox("Tipo", ["all", "expense", "income"])
    with col_f3:
        # Filtro por conta
        accounts = []
        try:
            accounts = personal_finance_agent.list_accounts(active_only=True)
        except Exception:
            pass
        account_options = [("Todas as contas", None)] + [(f"{a['icon']} {a['name']}", a["id"]) for a in accounts]
        selected_account = st.selectbox(
            "Conta",
            range(len(account_options)),
            format_func=lambda i: account_options[i][0],
        )
        filter_account_id = account_options[selected_account][1]
    with col_f4:
        limit_n = st.number_input("Máximo", min_value=10, max_value=200, value=50)

    with st.spinner("Buscando transações..."):
        try:
            tx_type = None if filter_type == "all" else filter_type
            tx_list = personal_finance_agent.list_transactions(
                limit=limit_n, days=filter_days, transaction_type=tx_type,
                account_id=filter_account_id,
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
                                f"font-weight: 700;'>{tipo_icon} {format_currency(tx['amount'])}</span>",
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
                        f"{format_currency(c['budget_limit'] / 100)}"
                        if c.get("budget_limit") else "-"
                    )
                    rows.append({
                        "ID": c["id"],
                        "Ícone": c.get("icon", "📦"),
                        "Nome": c["name"],
                        "Limite": limit_str,
                    })
                st.dataframe(rows, width='stretch', hide_index=True)
            else:
                st.info("Nenhuma categoria cadastrada.")
        except Exception as e:
            st.error(f"Erro: {e}")


def _tab_budget(personal_finance_agent):
    st.markdown("### 💰 Orçamento Mensal")

    col1, col2 = st.columns(2)
    with col1:
        year = st.number_input("Ano", min_value=2020, max_value=2030, value=datetime.now().year, key="budget_year")
    with col2:
        month = st.number_input("Mês", min_value=1, max_value=12, value=datetime.now().month, key="budget_month")

    with st.spinner("Carregando orçamento..."):
        try:
            data = personal_finance_agent.get_budget_overview(year, month)

            # ── Resumo geral ──
            total_budget = data["total_budget"]
            total_spent = data["total_spent"]
            remaining = total_budget - total_spent
            overall_pct = data["overall_percent"]

            st.markdown(f"**📊 Resumo — {month:02d}/{year}**")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 Orçamento Total", f"{format_currency(total_budget)}")
            m2.metric("💸 Gasto no Mês", f"{format_currency(total_spent)}")
            m3.metric("🏦 Restante", format_currency(remaining))
            m4.metric("📊 Consumido", f"{overall_pct:.1f}%")

            # Barra de progresso geral
            st.progress(min(overall_pct / 100, 1.0))
            if overall_pct >= 100:
                st.error(f"⚠️ Orçamento estourado em {overall_pct - 100:.1f}%!")
            elif overall_pct >= 80:
                st.warning(f"⚠️ {overall_pct:.1f}% do orçamento já consumido.")
            else:
                st.success(f"✅ {overall_pct:.1f}% consumido — dentro do planejado.")

            st.markdown("---")

            # ── Categorias detalhadas ──
            if data["categories"]:
                st.markdown("### 📋 Por Categoria")

                for c in data["categories"]:
                    cat_id = c["id"]
                    spent = c["spent"]
                    budget = c.get("budget_limit")
                    pct = c["percent"]
                    status = c["status"]

                    col_info, col_bar, col_edit = st.columns([2, 3, 1])

                    with col_info:
                        icon = c.get("icon", "📦")
                        color = c.get("color", "#6C757D")
                        st.markdown(
                            f"<span style='color: {color}; font-size: 1.2em;'>{icon}</span> "
                            f"**{c['name']}**",
                            unsafe_allow_html=True,
                        )
                        if budget is not None:
                            st.caption(f"{format_currency(spent)} de {format_currency(budget)}")
                        else:
                            st.caption(f"{format_currency(spent)} — sem limite definido")

                    with col_bar:
                        if budget is not None:
                            # Barra colorida conforme status
                            bar_pct = min(pct / 100, 1.0)
                            st.progress(bar_pct)
                            if status == "exceeded":
                                st.error(f"🔴 Estourado! ({pct:.1f}%)")
                            elif status == "warning":
                                st.warning(f"🟡 Atenção! ({pct:.1f}%)")
                            elif status == "attention":
                                st.info(f"🟠 {pct:.1f}% consumido")
                            else:
                                st.success(f"🟢 {pct:.1f}% — tranquilo")
                        else:
                            st.caption("⚪ Sem orçamento definido")
                            st.progress(0.0)

                    with col_edit:
                        with st.popover("✏️ Definir"):
                            new_limit = st.number_input(
                                "Limite (R$)", min_value=0.0, format="%.2f",
                                value=budget if budget else 0.0,
                                key=f"budget_input_{cat_id}",
                            )
                            if st.button("💾 Salvar", key=f"budget_save_{cat_id}"):
                                with st.spinner("Salvando..."):
                                    try:
                                        updated = personal_finance_agent.set_category_budget(
                                            cat_id, new_limit
                                        )
                                        if updated:
                                            st.success(f"✅ Orçamento de {c['name']} atualizado!")
                                            st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro: {e}")

                    st.markdown("---")

        except Exception as e:
            st.error(f"Erro ao carregar orçamento: {e}")


def _tab_accounts(personal_finance_agent):
    st.markdown("### 🏦 Contas Financeiras")

    with st.spinner("Carregando contas..."):
        try:
            accounts = personal_finance_agent.list_accounts(active_only=True)

            if accounts:
                cols = st.columns(min(len(accounts), 3))
                for i, acc in enumerate(accounts):
                    with cols[i % 3]:
                        with st.container(border=True):
                            icon = acc.get("icon", "🏦")
                            color = acc.get("color", "#06D6A0")
                            type_names = {
                                "checking": "Conta Corrente", "savings": "Poupança",
                                "credit_card": "Cartão de Crédito", "investment": "Investimento",
                                "cash": "Dinheiro", "other": "Outro",
                            }
                            st.markdown(f"### {icon} {acc['name']}")
                            st.caption(type_names.get(acc["account_type"], acc["account_type"]))
                            saldo_color = "var(--positive)" if acc["balance"] >= 0 else "var(--negative)"
                            st.markdown(
                                f"<span style='font-size: 1.4em; color: {saldo_color}; font-weight: 700;'>"
                                f"{format_currency(acc['balance'])}</span>",
                                unsafe_allow_html=True,
                            )
                            if acc.get("notes"):
                                st.caption(acc["notes"])

            else:
                st.info("Nenhuma conta cadastrada. Use 'stonks init' para criar contas padrão.")

        except Exception as e:
            st.error(f"Erro ao carregar contas: {e}")

    # ── Criar nova conta ──
    st.markdown("---")
    with st.expander("➕ Criar Nova Conta"):
        with st.form("new_account"):
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                acc_name = st.text_input("Nome da Conta")
                acc_type = st.selectbox("Tipo", ["checking", "savings", "credit_card", "investment", "cash", "other"],
                                        format_func=lambda x: {
                                            "checking": "Conta Corrente", "savings": "Poupança",
                                            "credit_card": "Cartão de Crédito", "investment": "Investimento",
                                            "cash": "Dinheiro", "other": "Outro",
                                        }.get(x, x))
            with col_a2:
                acc_balance = st.number_input("Saldo Inicial (R$)", value=0.0, format="%.2f")
                acc_icon = st.selectbox("Ícone", ["🏦", "💳", "💰", "📈", "💵", "🐷", "🏠", "📦"])

            acc_notes = st.text_area("Observações (opcional)")

            if st.form_submit_button("🏦 Criar Conta"):
                if not acc_name.strip():
                    st.error("Nome é obrigatório.")
                else:
                    with st.spinner("Criando..."):
                        try:
                            personal_finance_agent.create_account(
                                name=acc_name.strip(),
                                account_type=acc_type,
                                balance=acc_balance,
                                icon=acc_icon,
                                notes=acc_notes or None,
                            )
                            st.success(f"✅ Conta '{acc_name}' criada!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")
