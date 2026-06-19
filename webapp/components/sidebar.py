"""
Sidebar de navegacao do Stonks AI — WebApp Local.
"""

import streamlit as st

from stonks_ai import __version__
from stonks_ai.config import config
from stonks_ai.database import db

NAV_ITEMS = [
    ("🏠", "Dashboard", "dashboard"),
    ("💬", "Chat Financeiro", "chat"),
    ("💲", "Cotação", "quote"),
    ("📈", "Histórico", "history"),
    ("🤖", "Análise IA", "analyze"),
    ("⚖️", "Comparar", "compare"),
    ("📋", "Watchlist", "watchlist"),
    ("💰", "Finanças", "finance"),
    ("🎯", "Metas", "goals"),
    ("🔔", "Alertas", "alerts"),
    ("⚙️", "Configuração", "config"),
]


def render_sidebar():
    """Renderiza a barra lateral com navegacao e status do sistema."""
    with st.sidebar:
        # ── Logo e titulo ──────────────────────────────────────────
        st.markdown("""
        <div style="text-align: center; margin-bottom: 1.2rem;">
            <div style="font-size: 2.2rem; margin-bottom: 0.3rem;">🚀</div>
            <div style="font-size: 1.3rem; font-weight: 800;
                        background: linear-gradient(135deg, #00c853, #00e676);
                        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                        background-clip: text;">
                Stonks AI
            </div>
            <div style="font-size: 0.75rem; color: #606078; margin-top: 0.2rem;">
                v""" + __version__ + """ · Financeiro + IA
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Navegacao ──────────────────────────────────────────────
        st.markdown(
            '<p style="font-size: 0.7rem; font-weight: 700; text-transform: uppercase; '
            'letter-spacing: 1px; color: #606078; margin-bottom: 0.3rem; padding: 0 4px;">'
            '📍 Navegação</p>',
            unsafe_allow_html=True,
        )

        current_page = st.session_state.get("page", "dashboard")

        for icon, label, page_id in NAV_ITEMS:
            is_active = current_page == page_id

            # Indicador visual da pagina ativa
            if is_active:
                st.markdown(
                    '<div style="display: flex; align-items: center; margin: 2px 0;">'
                    '<div style="width: 3px; height: 24px; '
                    'background: linear-gradient(180deg, #00c853, #00e676); '
                    'border-radius: 0 4px 4px 0; margin-right: 8px; '
                    'box-shadow: 0 0 10px rgba(0,200,83,0.3); flex-shrink: 0;"></div>',
                    unsafe_allow_html=True,
                )

            if st.button(
                f"{icon}  {label}",
                key=f"nav_{page_id}",
                help=f"Abrir {label}",
                use_container_width=True,
            ):
                st.session_state["page"] = page_id
                st.session_state["quick_ticker"] = ""
                st.rerun()

            if is_active:
                st.markdown("</div>", unsafe_allow_html=True)

        # ── Status do sistema ──────────────────────────────────────
        st.markdown("---")
        st.markdown(
            '<p style="font-size: 0.7rem; font-weight: 700; text-transform: uppercase; '
            'letter-spacing: 1px; color: #606078; margin-bottom: 0.5rem;">'
            '🖥️ Estado do Sistema</p>',
            unsafe_allow_html=True,
        )

        # Base de dados
        try:
            db_ok = db.health_check()
            icon = "🟢" if db_ok else "🔴"
            status = "Online" if db_ok else "Offline"
            st.markdown(
                f'<p style="font-size: 0.85rem; color: #a0a0b0; margin: 4px 0;">'
                f'{icon} Base de Dados: {status}</p>',
                unsafe_allow_html=True,
            )
        except Exception:
            st.markdown(
                '<p style="font-size: 0.85rem; color: #ff1744; margin: 4px 0;">'
                '🔴 Base de Dados: Erro</p>',
                unsafe_allow_html=True,
            )

        # LLM
        try:
            from stonks_ai.agents.financial_agent import FinancialAgent

            fa = FinancialAgent()
            llm_ok = fa.check_llm_available()
            llm_model = config.get("llm", "model", default="N/A")
            llm_provider = config.get("llm", "provider", default="ollama")
            icon = "🟢" if llm_ok else "🟡"
            status = "Online" if llm_ok else "Offline"
            st.markdown(
                f'<p style="font-size: 0.85rem; color: #a0a0b0; margin: 4px 0;">'
                f'{icon} IA: {status}</p>'
                f'<p style="font-size: 0.7rem; color: #606078; margin: 0 0 0 20px;">'
                f'{llm_provider} · {llm_model}</p>',
                unsafe_allow_html=True,
            )
        except Exception:
            st.markdown(
                '<p style="font-size: 0.85rem; color: #ffab00; margin: 4px 0;">'
                '🟡 IA: Indisponível</p>',
                unsafe_allow_html=True,
            )

        # ── Rodapé ─────────────────────────────────────────────────
        st.markdown("---")
        st.markdown(
            f'<p style="font-size: 0.7rem; color: #606078; text-align: center; margin: 0;">'
            f'Stonks AI v{__version__}<br>B3 · NYSE · Finanças · IA</p>',
            unsafe_allow_html=True,
        )
