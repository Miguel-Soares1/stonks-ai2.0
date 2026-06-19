"""Página Metas Financeiras — criação e acompanhamento de objetivos."""

from datetime import datetime

import streamlit as st


def page_goals(financial_agent, personal_finance_agent):
    st.markdown("## 🎯 Metas Financeiras")

    tab1, tab2 = st.tabs(["📋 Metas", "➕ Nova Meta"])

    with tab1:
        _tab_list_goals(personal_finance_agent)
    with tab2:
        _tab_create_goal(personal_finance_agent)

    # Diálogos auxiliares
    _render_delete_dialog(personal_finance_agent)
    _render_edit_form(personal_finance_agent)


def _tab_list_goals(personal_finance_agent):
    status_filter = st.selectbox("Status", ["active", "completed", "all"])
    with st.spinner("Carregando metas..."):
        try:
            sf = None if status_filter == "all" else status_filter
            goals_list = personal_finance_agent.list_goals(status=sf)

            if goals_list:
                for g in goals_list:
                    pct = g.get("progress_percent", 0)
                    goal_id = g["id"]

                    with st.container(border=True):
                        col_info, col_contrib, col_actions = st.columns([2, 1, 1])

                        with col_info:
                            icon = g.get("icon", "🎯")
                            st.markdown(f"**{icon} {g['name']}**")
                            st.progress(min(pct / 100, 1.0))
                            st.caption(
                                f"R$ {g['current_amount']:,.2f} / "
                                f"R$ {g['target_amount']:,.2f} ({pct:.1f}%)"
                            )
                            extra_info = []
                            gt = g.get("goal_type", "")
                            if gt:
                                extra_info.append(f"Tipo: {gt}")
                            extra_info.append(f"Prioridade: {g.get('priority', 'medium')}")
                            if g.get("deadline"):
                                d = g["deadline"]
                                d_str = d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else str(d)[:10]
                                extra_info.append(f"📅 {d_str}")
                            st.caption(" · ".join(extra_info))

                        with col_contrib:
                            if g["status"] == "active":
                                contrib = st.number_input(
                                    "Valor", min_value=0.01, key=f"contrib_{goal_id}",
                                    label_visibility="collapsed", placeholder="R$",
                                )
                                if st.button("➕ Contribuir", key=f"btn_{goal_id}"):
                                    if contrib > 0:
                                        with st.spinner("Atualizando..."):
                                            try:
                                                updated = personal_finance_agent.contribute_to_goal(goal_id, contrib)
                                                st.success(f"✅ R$ {contrib:,.2f} adicionado!")
                                                if updated["status"] == "completed":
                                                    st.balloons()
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"Erro: {e}")

                        with col_actions:
                            st.markdown("###### Ações")
                            if st.button("✏️ Editar", key=f"edit_goal_{goal_id}", use_container_width=True):
                                st.session_state["edit_goal_id"] = goal_id
                                st.session_state["edit_goal_data"] = g
                                st.rerun()
                            if st.button("🗑️ Excluir", key=f"del_goal_{goal_id}", use_container_width=True):
                                st.session_state["del_goal_id"] = goal_id
                                st.session_state["del_goal_name"] = g["name"]
                                st.rerun()
            else:
                st.info("Nenhuma meta encontrada.")
        except Exception as e:
            st.error(f"Erro: {e}")


def _tab_create_goal(personal_finance_agent):
    with st.form("new_goal"):
        name = st.text_input("Nome da Meta*")
        target = st.number_input("Valor Alvo (R$)*", min_value=0.01, format="%.2f")
        col_c, col_d = st.columns(2)
        with col_c:
            deadline = st.date_input("Prazo (opcional)", value=None)
        with col_d:
            goal_type = st.selectbox("Tipo", ["savings", "debt", "investment", "custom"])
        priority = st.selectbox("Prioridade", ["low", "medium", "high"])
        description = st.text_area("Descrição (opcional)")

        if st.form_submit_button("🎯 Criar Meta"):
            if not name.strip():
                st.error("Nome é obrigatório.")
            else:
                with st.spinner("Criando meta..."):
                    try:
                        deadline_str = deadline.strftime("%Y-%m-%d") if deadline else None
                        goal = personal_finance_agent.create_goal(
                            name=name.strip(),
                            target_amount=target,
                            deadline=deadline_str,
                            goal_type=goal_type,
                            priority=priority,
                            description=description or None,
                        )
                        st.success(f"✅ Meta '{goal['name']}' criada!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")


def _render_delete_dialog(personal_finance_agent):
    if "del_goal_id" in st.session_state and st.session_state["del_goal_id"]:
        del_id = st.session_state["del_goal_id"]
        del_name = st.session_state.get("del_goal_name", "")
        st.markdown("---")
        st.warning(f"🗑️ **Confirmar exclusão** — {del_name}")
        col_c1, col_c2, col_c3 = st.columns([1, 1, 2])
        with col_c1:
            if st.button("✅ Sim, excluir", type="primary", key="confirm_del_goal"):
                with st.spinner("Excluindo..."):
                    try:
                        personal_finance_agent.delete_goal(del_id)
                        st.success("✅ Meta excluída!")
                        st.session_state["del_goal_id"] = None
                        st.session_state["del_goal_name"] = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao excluir: {e}")
        with col_c2:
            if st.button("❌ Cancelar", key="cancel_del_goal"):
                st.session_state["del_goal_id"] = None
                st.session_state["del_goal_name"] = None
                st.rerun()


def _render_edit_form(personal_finance_agent):
    if "edit_goal_id" in st.session_state and st.session_state["edit_goal_id"]:
        goal_data = st.session_state.get("edit_goal_data", {})
        st.markdown("---")
        st.markdown(f"### ✏️ Editando Meta: {goal_data.get('name', '')}")

        with st.form("edit_goal"):
            edit_name = st.text_input("Nome da Meta", value=goal_data.get("name", ""))
            edit_target = st.number_input(
                "Valor Alvo (R$)", min_value=0.01, format="%.2f",
                value=float(goal_data.get("target_amount", 0)),
            )

            col_e1, col_e2 = st.columns(2)
            with col_e1:
                raw_deadline = goal_data.get("deadline", "")
                if hasattr(raw_deadline, "strftime"):
                    default_deadline = datetime.strptime(raw_deadline.strftime("%Y-%m-%d"), "%Y-%m-%d")
                elif raw_deadline:
                    default_deadline = datetime.strptime(str(raw_deadline)[:10], "%Y-%m-%d")
                else:
                    default_deadline = None
                edit_deadline = st.date_input("Prazo (opcional)", value=default_deadline)
            with col_e2:
                edit_goal_type = st.selectbox(
                    "Tipo", ["savings", "debt", "investment", "custom"],
                    index=["savings", "debt", "investment", "custom"].index(
                        goal_data.get("goal_type", "savings")
                    ),
                )

            col_e3, col_e4 = st.columns(2)
            with col_e3:
                edit_priority = st.selectbox(
                    "Prioridade", ["low", "medium", "high"],
                    index=["low", "medium", "high"].index(goal_data.get("priority", "medium")),
                )
            with col_e4:
                edit_status = st.selectbox(
                    "Status", ["active", "completed", "cancelled", "paused"],
                    index=["active", "completed", "cancelled", "paused"].index(
                        goal_data.get("status", "active")
                    ),
                )

            edit_description = st.text_area("Descrição", value=goal_data.get("description") or "")

            col_s1, col_s2, col_s3 = st.columns([1, 1, 2])
            with col_s1:
                submitted = st.form_submit_button("💾 Salvar", type="primary")
            with col_s2:
                cancelled = st.form_submit_button("❌ Cancelar")

            if submitted:
                if not edit_name.strip():
                    st.error("Nome é obrigatório.")
                else:
                    with st.spinner("Salvando..."):
                        try:
                            updated = personal_finance_agent.update_goal(
                                goal_id=st.session_state["edit_goal_id"],
                                name=edit_name.strip(),
                                target_amount=edit_target,
                                deadline=edit_deadline.strftime("%Y-%m-%d") if edit_deadline else None,
                                goal_type=edit_goal_type,
                                priority=edit_priority,
                                description=edit_description.strip() or None,
                                status=edit_status,
                            )
                            if updated:
                                st.success("✅ Meta atualizada!")
                            else:
                                st.error("❌ Meta não encontrada.")
                            st.session_state["edit_goal_id"] = None
                            st.session_state["edit_goal_data"] = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")

            if cancelled:
                st.session_state["edit_goal_id"] = None
                st.session_state["edit_goal_data"] = None
                st.rerun()
