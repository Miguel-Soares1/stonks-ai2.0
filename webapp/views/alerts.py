"""Página Alertas Inteligentes."""

import streamlit as st


def page_alerts(financial_agent, personal_finance_agent):
    st.markdown("## 🔔 Alertas Inteligentes")

    col_ref, col_check = st.columns([1, 1])
    with col_ref:
        show_all = st.checkbox("Mostrar já dispensados", value=False)
    with col_check:
        if st.button("🔄 Verificar Novos Alertas", use_container_width=True):
            with st.spinner("Verificando..."):
                try:
                    new = personal_finance_agent.check_alerts()
                    if new:
                        st.success(f"✅ {len(new)} novo(s) alerta(s) gerado(s)!")
                    else:
                        st.info("Nenhum novo alerta necessário.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")

    with st.spinner("Carregando alertas..."):
        try:
            alerts_list = personal_finance_agent.list_alerts(active_only=not show_all)

            if alerts_list:
                for a in alerts_list:
                    sev_icon = {
                        "high": "🔴", "medium": "🟡", "low": "🟢",
                    }.get(a["severity"], "⚪")

                    with st.container(border=True):
                        cols = st.columns([5, 1])
                        with cols[0]:
                            st.markdown(f"{sev_icon} **{a.get('title', 'Alerta')}**")
                            st.caption(f"Tipo: {a.get('alert_type', '-')}")
                            msg = a.get("message", "")
                            if msg:
                                st.text(msg[:200])
                            d = a.get("created_at", "")
                            d_str = d.strftime("%d/%m/%Y %H:%M") if hasattr(d, "strftime") else str(d)[:16]
                            st.caption(f"🕐 {d_str}")
                        with cols[1]:
                            if not a.get("dismissed"):
                                if st.button("✅ Dispensar", key=f"dismiss_{a['id']}"):
                                    personal_finance_agent.dismiss_alert(a["id"])
                                    st.rerun()
            else:
                st.success("✅ Nenhum alerta pendente!")
        except Exception as e:
            st.error(f"Erro ao carregar alertas: {e}")
