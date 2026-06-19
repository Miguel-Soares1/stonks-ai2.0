"""Página Configuração do sistema."""

import yaml
import streamlit as st

from stonks_ai import __version__
from stonks_ai.config import config, ConfigError
from stonks_ai.database import DatabaseError, db
from stonks_ai.utils.formatters import _mask_user_path, sanitize_config_for_display


def page_config(financial_agent, personal_finance_agent):
    st.markdown('<div class="main-header">⚙️ Configuração</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📋 Visualizar", "✏️ Editar", "🛠️ Sistema"])

    with tab1:
        st.markdown("### Configuração Atual")
        clean_config = sanitize_config_for_display(config.data)
        config_yaml = yaml.dump(clean_config, default_flow_style=False, allow_unicode=True)
        st.code(config_yaml, language="yaml")

    with tab2:
        st.markdown("### Alterar Configuração")

        col1, col2 = st.columns(2)
        with col1:
            provider = st.selectbox(
                "Provider LLM",
                ["ollama", "deepseek", "openai", "openai_compatible"],
                index=["ollama", "deepseek", "openai", "openai_compatible"].index(
                    config.get("llm", "provider", default="ollama")
                ),
                key="cfg_llm_provider",
            )
            llm_model = st.text_input(
                "Modelo LLM",
                value=config.get("llm", "model", default="llama3.2:3b"),
                key="cfg_llm_model",
            )
            llm_temp = st.slider(
                "Temperatura LLM",
                min_value=0.0, max_value=2.0,
                value=config.get("llm", "temperature", default=0.3),
                step=0.1, key="cfg_llm_temp",
            )
            llm_endpoint = st.text_input(
                "Endpoint Ollama",
                value=config.get("llm", "endpoint", default="http://localhost:11434"),
                key="cfg_llm_endpoint",
            )

        with col2:
            api_key = st.text_input(
                "API Key (remoto)",
                value=config.get("llm", "api_key", default=""),
                type="password",
                placeholder="Ou use ${ENV_VAR}",
                key="cfg_llm_api_key",
            )
            base_url = st.text_input(
                "Base URL (openai_compatible)",
                value=config.get("llm", "base_url", default=""),
                placeholder="https://api.openai.com/v1",
                key="cfg_llm_base_url",
            )
            default_exchange = st.selectbox(
                "Bolsa padrão",
                ["B3", "NYSE"],
                index=0 if config.get("stocks", "default_exchange") == "B3" else 1,
                key="cfg_default_exchange",
            )
            fallback = st.selectbox(
                "Fallback Provider",
                ["ollama", "none"],
                index=0 if config.get("llm", "fallback_provider") == "ollama" else 1,
                key="cfg_fallback",
            )

        if st.button("💾 Salvar Configuração", type="primary"):
            try:
                config.set(provider, "llm", "provider")
                config.set(llm_model, "llm", "model")
                config.set(llm_temp, "llm", "temperature")
                config.set(llm_endpoint, "llm", "endpoint")
                config.set(api_key, "llm", "api_key")
                config.set(base_url, "llm", "base_url")
                config.set(default_exchange, "stocks", "default_exchange")
                config.set(fallback if fallback != "none" else "", "llm", "fallback_provider")
                st.success("✅ Configuração salva com sucesso!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Erro ao salvar: {e}")

    with tab3:
        st.markdown("### 🛠️ Ferramentas do Sistema")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗄️ Inicializar Banco de Dados", type="primary"):
                try:
                    db.initialize()
                    st.success("✅ Banco de dados inicializado com sucesso!")
                except DatabaseError as e:
                    st.error(f"❌ {e}")

            if st.button("🔄 Recarregar Configuração"):
                try:
                    config._load()
                    st.success("✅ Configuração recarregada!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro: {e}")

        with col2:
            if st.button("🔍 Verificar Conexão LLM"):
                if financial_agent.check_llm_available():
                    st.success("✅ LLM está online!")
                else:
                    st.warning(
                        "⚠️ LLM não está disponível. Verifique as configurações."
                    )

            if st.button("🔍 Verificar Banco de Dados"):
                if db.health_check():
                    st.success(f"✅ Banco OK em: {db.db_path}")
                else:
                    st.error("❌ Banco de dados com problemas.")

        st.markdown("### ℹ️ Informações do Sistema")
        info_col1, info_col2 = st.columns(2)
        with info_col1:
            st.markdown(f"**Versão:** {__version__}")
            st.markdown(f"**Banco:** {_mask_user_path(str(db.db_path))}")
        with info_col2:
            st.markdown(f"**Config:** {_mask_user_path(str(config.config_path))}")
            st.markdown(
                f"**LLM:** {config.get('llm', 'provider', default='N/A')} · "
                f"{config.get('llm', 'model', default='N/A')}"
            )
