"""
Stonks AI - Web Application (Streamlit).

Interface web para o assistente financeiro com IA.
Reusa todos os agentes e coletores existentes.

Uso:
    streamlit run webapp/app.py

Estrutura modular (~90 linhas vs 2144 originais):
    webapp/
    ├── app.py              # Router principal
    ├── theme.py            # Tema CSS escuro
    ├── components/         # Componentes reutilizaveis
    └── pages/              # Paginas da aplicacao
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from stonks_ai.agents.financial_agent import FinancialAgent
from stonks_ai.agents.personal_finance_agent import PersonalFinanceAgent
from webapp.components.sidebar import render_sidebar
from webapp.views import PAGE_REGISTRY
from webapp.theme import get_theme_css

st.set_page_config(
    page_title="Stonks AI",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(get_theme_css(), unsafe_allow_html=True)


@st.cache_resource
def get_financial_agent() -> FinancialAgent:
    return FinancialAgent()


@st.cache_resource
def get_personal_finance_agent() -> PersonalFinanceAgent:
    return PersonalFinanceAgent()


def main():
    financial_agent = get_financial_agent()
    personal_finance_agent = get_personal_finance_agent()

    render_sidebar()

    if "page" not in st.session_state:
        st.session_state["page"] = "dashboard"

    current_page = st.session_state.get("page", "dashboard")
    page_func = PAGE_REGISTRY.get(current_page, PAGE_REGISTRY["dashboard"])
    page_func(financial_agent, personal_finance_agent)


if __name__ == "__main__":
    main()
