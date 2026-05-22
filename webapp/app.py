"""
Stonks AI - Web Application (Streamlit).

Interface web para o assistente financeiro com IA.
Reusa todos os agentes e coletores existentes.

Uso:
    streamlit run webapp/app.py
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# Garante que o pacote raiz está no path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from stonks_ai import __version__
from stonks_ai.agents.financial_agent import FinancialAgent
from stonks_ai.agents.personal_finance_agent import PersonalFinanceAgent
from stonks_ai.collectors.stocks.base import StockCollectorError
from stonks_ai.config import ConfigError, config
from stonks_ai.database import DatabaseError, db
from stonks_ai.llm.client import LLMError
from stonks_ai.utils.formatters import (
    format_change,
    format_currency,
    format_large_number,
    format_percent,
    format_ticker_display,
)
from stonks_ai.utils.validators import detect_exchange

# ── Configuração da página ──────────────────────────────────────────────
st.set_page_config(
    page_title="Stonks AI",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS do tema escuro ──────────────────────────────────────────────────
def get_theme_css() -> str:
    """Retorna CSS customizado do tema escuro (preto e verde)."""
    return """
<style>
    :root {
        --bg-primary: #0a0a0a;
        --bg-secondary: #0d0d0d;
        --bg-card: #111111;
        --bg-hover: #1a2a1a;
        --border-color: #1a3a1a;
        --text-primary: #e0e0e0;
        --text-secondary: #aaaaaa;
        --text-muted: #666666;
        --accent-primary: #00b85e;
        --accent-secondary: #008c49;
        --accent-glow: rgba(0, 184, 94, 0.15);
        --positive: #00b85e;
        --negative: #ff4444;
        --neutral: #cccccc;
        --sidebar-bg: #0a0a0a;
        --sidebar-border: #1a3a1a;
        --ai-box-bg: #0d1a11;
        --ai-box-border: #1a3a1a;
        --input-bg: #111111;
        --shadow: 0 2px 8px rgba(0, 184, 94, 0.05);
    }

    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: var(--accent-primary);
        margin-bottom: 0.5rem;
        text-shadow: 0 0 20px var(--accent-glow);
    }
    .sub-header {
        font-size: 1.2rem;
        color: var(--text-secondary);
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: var(--bg-card);
        border-radius: 12px;
        padding: 1.2rem;
        border: 1px solid var(--border-color);
        text-align: center;
        transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: var(--accent-primary);
        box-shadow: 0 4px 20px var(--accent-glow);
    }
    .metric-label {
        color: var(--text-muted);
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        margin-top: 0.2rem;
    }
    .metric-value.positive { color: var(--positive); }
    .metric-value.negative { color: var(--negative); }
    .metric-value.neutral  { color: var(--neutral); }
    .info-box {
        background: var(--bg-card);
        border-radius: 10px;
        padding: 1rem;
        border-left: 4px solid var(--accent-primary);
        margin: 0.5rem 0;
        box-shadow: var(--shadow);
    }
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary)) !important;
        border: none !important;
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    .stButton > button[kind="primary"]:hover {
        opacity: 0.9;
        transform: translateY(-1px);
        box-shadow: 0 4px 16px var(--accent-glow) !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: var(--bg-secondary);
        padding: 4px;
        border-radius: 10px;
        border: 1px solid var(--border-color);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 20px;
        font-weight: 600;
        transition: all 0.2s;
        color: var(--text-secondary) !important;
    }
    .stTabs [aria-selected="true"] {
        background: var(--accent-primary) !important;
        color: #ffffff !important;
    }
    [data-testid="stSidebar"] {
        background: var(--sidebar-bg);
        border-right: 1px solid var(--sidebar-border);
    }
    /* Sidebar navigation buttons */
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div > div > div.stButton button {
        background: transparent !important;
        border: none !important;
        padding: 10px 14px !important;
        border-radius: 10px !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        text-align: left !important;
        color: var(--text-primary) !important;
        transition: all 0.2s !important;
        box-shadow: none !important;
        width: 100% !important;
        justify-content: flex-start !important;
    }
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div > div > div.stButton button:hover {
        background: var(--bg-hover) !important;
        color: var(--accent-primary) !important;
    }
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div > div > div.stButton button:focus {
        box-shadow: none !important;
    }
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div > div > div.stButton button p {
        color: inherit !important;
        font-size: 0.9rem !important;
        font-weight: inherit !important;
    }
    /* Active nav indicator */
    .nav-active-indicator {
        width: 3px;
        height: 28px;
        background: var(--accent-primary);
        border-radius: 0 4px 4px 0;
        margin: 4px 0;
        box-shadow: 0 0 8px var(--accent-glow);
        flex-shrink: 0;
    }
    .stSpinner > div {
        border-top-color: var(--accent-primary) !important;
    }
    .stChatInputContainer {
        max-width: 100%;
    }
    div[data-testid="stNotification"] {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
    }
    [data-testid="stChatMessage"] {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 0.5rem 1rem;
        margin-bottom: 0.5rem;
    }
    .streamlit-expanderHeader {
        background: var(--bg-card);
        border-radius: 10px;
        border: 1px solid var(--border-color);
    }
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid var(--border-color);
    }
    .stTextInput input, .stSelectbox div, .stNumberInput input {
        background: var(--input-bg) !important;
        border-radius: 8px !important;
        border: 1px solid var(--border-color) !important;
        color: var(--text-primary) !important;
    }
    .stTextInput input:focus, .stSelectbox div:focus {
        border-color: var(--accent-primary) !important;
        box-shadow: 0 0 0 2px var(--accent-glow) !important;
    }
    .stApp {
        background: var(--bg-primary);
    }
    .main > div {
        background: var(--bg-primary);
    }
    p, h1, h2, h3, h4, h5, h6, span, label, li {
        color: var(--text-primary);
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label {
        color: var(--text-primary);
    }
    .stSlider div[data-baseweb="slider"] div {
        background: var(--accent-primary);
    }
    .stProgress div div {
        background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
    }
    .theme-toggle-btn {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 30px;
        padding: 8px 16px;
        cursor: pointer;
        font-size: 0.9rem;
        font-weight: 600;
        transition: all 0.3s;
        display: flex;
        align-items: center;
        gap: 8px;
        width: 100%;
        justify-content: center;
        color: var(--text-primary);
    }
    .theme-toggle-btn:hover {
        border-color: var(--accent-primary);
        box-shadow: 0 0 16px var(--accent-glow);
    }
    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-track {
        background: var(--bg-secondary);
    }
    ::-webkit-scrollbar-thumb {
        background: var(--border-color);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: var(--accent-primary);
    }
</style>
"""


# ── Aplica o CSS do tema escuro ─────────────────────────────────────────
st.markdown(get_theme_css(), unsafe_allow_html=True)


# ── Inicialização dos agentes (singletons na sessão) ────────────────────
@st.cache_resource
def get_financial_agent() -> FinancialAgent:
    return FinancialAgent()


@st.cache_resource
def get_personal_finance_agent() -> PersonalFinanceAgent:
    return PersonalFinanceAgent()


financial_agent = get_financial_agent()
personal_finance_agent = get_personal_finance_agent()


# ── Utilitários da interface ────────────────────────────────────────────
def color_for_change(value: float) -> str:
    """Retorna classe CSS baseada na variação."""
    if value > 0:
        return "positive"
    elif value < 0:
        return "negative"
    return "neutral"


def render_metric(label: str, value: str, change: Optional[float] = None):
    """Renderiza um card de métrica formatado."""
    css_class = ""
    if change is not None:
        css_class = color_for_change(change)
    st.markdown(
        f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value {css_class}">{value}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_info_box(title: str, content: str):
    """Renderiza uma caixa de informação estilizada."""
    st.markdown(
        f"""
    <div class="info-box">
        <strong>{title}</strong><br>
        {content}
    </div>
    """,
        unsafe_allow_html=True,
    )


def build_price_chart(
    data: List[Dict[str, Any]],
    ticker: str,
    title: str = "",
) -> go.Figure:
    """Constrói gráfico de velas (candlestick) com Plotly."""
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
    )

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df["date"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name=ticker,
            increasing_line_color="#00ff88",
            decreasing_line_color="#ff4444",
        ),
        row=1,
        col=1,
    )

    # Volume
    colors = [
        "#00ff88" if df["close"].iloc[i] >= df["open"].iloc[i] else "#ff4444"
        for i in range(len(df))
    ]
    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["volume"],
            name="Volume",
            marker_color=colors,
            opacity=0.6,
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        title=title or f"{ticker} - Preço Histórico",
        xaxis_title="Data",
        yaxis_title="Preço",
        template="plotly_dark",
        hovermode="x unified",
        margin=dict(l=40, r=40, t=40, b=40),
        height=600,
        showlegend=False,
        xaxis_rangeslider_visible=False,
    )

    fig.update_yaxes(title_text="Preço", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    return fig


def build_comparison_chart(
    datasets: Dict[str, pd.DataFrame],
    title: str = "Comparação (Base 100)",
) -> go.Figure:
    """Constrói gráfico de comparação normalizado (base 100)."""
    fig = go.Figure()

    colors = [
        "#00ff88", "#00cc6a", "#66ffaa", "#009955",
        "#33ee77", "#00bb55", "#88ffbb", "#00dd66",
    ]

    for i, (name, df) in enumerate(datasets.items()):
        if df.empty:
            continue
        base = df["close"].iloc[0]
        if base == 0:
            continue
        normalized = (df["close"] / base) * 100
        color = colors[i % len(colors)]
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=normalized,
                mode="lines",
                name=name,
                line=dict(width=2, color=color),
            )
        )

    fig.update_layout(
        title=title,
        xaxis_title="Data",
        yaxis_title="Variação % (Base 100)",
        template="plotly_dark",
        hovermode="x unified",
        margin=dict(l=40, r=40, t=40, b=40),
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )

    fig.add_hline(y=100, line_dash="dash", line_color="gray", opacity=0.5)

    return fig


# ── Navegação lateral com abas clicáveis ────────────────────────────────
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
    ("⚙️", "Config", "config"),
]

def render_sidebar():
    """Renderiza a barra lateral com navegação em abas e status."""
    with st.sidebar:
        # Logo e título
        st.markdown(
            f"""
        <div style="text-align: center; margin-bottom: 1.5rem;">
            <h1 style="font-size: 2.2rem; margin: 0;">🚀</h1>
            <h2 style="font-size: 1.3rem; margin: 0.2rem 0; 
                background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                background-clip: text;">
                Stonks AI
            </h2>
            <p style="font-size: 0.8rem; color: var(--text-muted); margin: 0;">
                v{__version__} · Financeiro + IA
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # ── Navegação em abas ──────────────────────────────────────────
        st.markdown(
            '<div style="font-size: 0.8rem; font-weight: 600; '
            'text-transform: uppercase; letter-spacing: 1px; '
            'color: var(--text-muted); margin-bottom: 0.5rem; padding: 0 4px;">'
            '📍 Navegação</div>',
            unsafe_allow_html=True,
        )

        current_page = st.session_state.get("page", "dashboard")

        for icon, label, page_id in NAV_ITEMS:
            is_active = current_page == page_id

            # Se for a página ativa, renderiza um indicador verde à esquerda
            if is_active:
                st.markdown(
                    '<div style="display: flex; align-items: center; gap: 0;">'
                    '<div class="nav-active-indicator"></div>',
                    unsafe_allow_html=True,
                )

            # Botão estilizado como item de navegação — o clique vai direto no nome
            if st.button(
                f"{icon} {label}",
                key=f"nav_{page_id}",
                help=f"Abrir {label}",
                use_container_width=True,
            ):
                st.session_state["page"] = page_id
                st.session_state["quick_ticker"] = ""
                st.rerun()

            if is_active:
                st.markdown("</div>", unsafe_allow_html=True)

        # ── Status do sistema ──────────────────────────────────────────
        st.markdown("---")
        st.markdown(
            '<div style="font-size: 0.8rem; font-weight: 600; '
            'text-transform: uppercase; letter-spacing: 1px; '
            'color: var(--text-muted); margin-bottom: 0.5rem; padding: 0 4px;">'
            '🖥️ Status</div>',
            unsafe_allow_html=True,
        )

        # Verifica banco
        try:
            db_ok = db.health_check()
            st.markdown(
                f'<div style="font-size: 0.85rem; color: var(--text-secondary); '
                f'padding: 2px 4px;">'
                f'{"🟢" if db_ok else "🔴"} Banco: {"Online" if db_ok else "Offline"}'
                f'</div>',
                unsafe_allow_html=True,
            )
        except Exception:
            st.markdown(
                '<div style="font-size: 0.85rem; color: var(--negative); '
                'padding: 2px 4px;">🔴 Banco: Erro</div>',
                unsafe_allow_html=True,
            )

        # Verifica LLM
        try:
            llm_ok = financial_agent.check_llm_available()
            llm_model = config.get("llm", "model", default="N/A")
            icon = "🟢" if llm_ok else "🟡"
            st.markdown(
                f'<div style="font-size: 0.85rem; color: var(--text-secondary); '
                f'padding: 2px 4px;">'
                f'{icon} LLM: {"Online" if llm_ok else "Offline"}'
                f'<br><span style="font-size: 0.75rem; color: var(--text-muted);">'
                f'Modelo: {llm_model}</span></div>',
                unsafe_allow_html=True,
            )
        except Exception:
            st.markdown(
                '<div style="font-size: 0.85rem; color: var(--negative); '
                'padding: 2px 4px;">🟡 LLM: Indisponível</div>',
                unsafe_allow_html=True,
            )

        # Versão
        st.markdown("---")
        st.markdown(
            f'<div style="font-size: 0.75rem; color: var(--text-muted); '
            f'text-align: center;">'
            f'Stonks AI v{__version__}<br>'
            f'B3 · NYSE · Finanças · IA'
            f'</div>',
            unsafe_allow_html=True,
        )


# ── Páginas ─────────────────────────────────────────────────────────────

def page_dashboard():
    """Página inicial com visão geral e atalhos."""
    st.markdown(
        '<div class="main-header">🚀 Stonks AI</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sub-header">'
        "Assistente financeiro inteligente — Ações B3/NYSE, Finanças Pessoais e IA Local"
        "</div>",
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric("Ações B3", "~400+", None)
    with col2:
        render_metric("Ações NYSE", "~6,000+", None)
    with col3:
        render_metric("Finanças Pessoais", "Ativo", None)
    with col4:
        llm_status = (
            "Online" if financial_agent.check_llm_available() else "Offline"
        )
        render_metric("IA Local", llm_status, None)

    st.markdown("### 🔥 Comece rápido")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**💲 Cotação**")
        ticker_quick = st.text_input(
            "Ticker",
            placeholder="Ex: PETR4, AAPL",
            key="dash_quote_ticker",
            label_visibility="collapsed",
        )
        if st.button("Ver Cotação", key="dash_quote_btn") and ticker_quick:
            st.session_state["page"] = "quote"
            st.session_state["quick_ticker"] = ticker_quick.upper()
            st.rerun()

    with col2:
        st.markdown("**🤖 Análise IA**")
        ticker_analyze = st.text_input(
            "Ticker",
            placeholder="Ex: VALE3, MSFT",
            key="dash_analyze_ticker",
            label_visibility="collapsed",
        )
        if st.button("Analisar", key="dash_analyze_btn") and ticker_analyze:
            st.session_state["page"] = "analyze"
            st.session_state["quick_ticker"] = ticker_analyze.upper()
            st.rerun()

    # Watchlist quick view
    st.markdown("---")
    st.markdown("### 📋 Watchlist Rápida")
    _render_watchlist_table(limit=5)


def page_quote():
    """Página de cotação de uma ação."""
    st.markdown(
        '<div class="main-header">💲 Cotação</div>',
        unsafe_allow_html=True,
    )

    ticker = st.text_input(
        "Ticker da ação",
        placeholder="Ex: PETR4, VALE3, AAPL, MSFT",
        value=st.session_state.get("quick_ticker", ""),
        key="quote_ticker_input",
    )

    exchange = st.selectbox(
        "Bolsa (deixe Auto para detecção automática)",
        ["Auto", "B3", "NYSE"],
        index=0,
        key="quote_exchange",
    )

    if st.button("🔍 Buscar Cotação", type="primary") and ticker:
        st.session_state["quick_ticker"] = ""
        with st.spinner(f"Buscando cotação de {ticker.upper()}..."):
            try:
                exch = None if exchange == "Auto" else exchange
                q = financial_agent.get_quote(ticker.upper(), exch)

                st.markdown(
                    f'<h2 style="color: var(--accent-primary);">'
                    f"{format_ticker_display(q.ticker, q.exchange)}"
                    f"</h2>",
                    unsafe_allow_html=True,
                )

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    render_metric(
                        "Preço",
                        format_currency(q.price, q.currency),
                        q.change_percent,
                    )
                with col2:
                    render_metric(
                        "Variação",
                        format_change(q.change, q.change_percent),
                        q.change_percent,
                    )
                with col3:
                    render_metric("Máxima", format_currency(q.high, q.currency))
                with col4:
                    render_metric("Mínima", format_currency(q.low, q.currency))

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    render_metric(
                        "Abertura", format_currency(q.open_price, q.currency)
                    )
                with col2:
                    render_metric(
                        "Fech. Ant.",
                        format_currency(q.previous_close, q.currency),
                    )
                with col3:
                    render_metric("Volume", format_large_number(q.volume))
                with col4:
                    render_metric("Empresa", q.name or "N/A")

                st.markdown("---")
                render_info_box(
                    "📌 Dica",
                    f"Use o menu **Histórico** para ver o gráfico de {q.ticker}, "
                    f"ou **Análise IA** para uma análise completa com inteligência artificial.",
                )

            except StockCollectorError as e:
                st.error(f"❌ {e}")
            except Exception as e:
                st.error(f"Erro inesperado: {e}")


def page_history():
    """Página de histórico com gráfico interativo."""
    st.markdown(
        '<div class="main-header">📈 Histórico</div>',
        unsafe_allow_html=True,
    )

    ticker = st.text_input(
        "Ticker da ação",
        placeholder="Ex: PETR4, AAPL",
        value=st.session_state.get("quick_ticker", ""),
        key="history_ticker_input",
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        exchange = st.selectbox(
            "Bolsa",
            ["Auto", "B3", "NYSE"],
            index=0,
            key="history_exchange",
        )
    with col2:
        period = st.selectbox(
            "Período",
            ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
            index=2,
            key="history_period",
        )
    with col3:
        interval = st.selectbox(
            "Intervalo",
            ["1d", "1h", "5m", "15m", "30m", "60m"],
            index=0,
            key="history_interval",
        )

    if st.button("📊 Gerar Gráfico", type="primary") and ticker:
        st.session_state["quick_ticker"] = ""
        with st.spinner(f"Buscando histórico de {ticker.upper()}..."):
            try:
                exch = None if exchange == "Auto" else exchange
                h = financial_agent.get_history(
                    ticker.upper(), exch, period=period, interval=interval
                )

                if not h.data:
                    st.warning(
                        f"⚠️ Nenhum dado histórico para {ticker} no período {period}."
                    )
                    return

                # Métricas resumo
                first = h.data[0]
                last = h.data[-1]
                change_val = last["close"] - first["close"]
                change_pct = (
                    (change_val / first["close"] * 100) if first["close"] else 0
                )

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    render_metric(
                        "Período",
                        f"{first['date'][:10]} → {last['date'][:10]}",
                    )
                with col2:
                    render_metric(
                        "Variação",
                        format_change(change_val, change_pct),
                        change_pct,
                    )
                with col3:
                    avg_price = sum(d["close"] for d in h.data) / len(h.data)
                    render_metric("Média", f"{avg_price:.2f}")
                with col4:
                    render_metric(
                        "Fechamento Atual",
                        f"{last['close']:.2f}",
                        change_pct,
                    )

                # Gráfico interativo
                fig = build_price_chart(
                    h.data,
                    ticker.upper(),
                    title=f"{ticker.upper()} - {period}",
                )
                st.plotly_chart(fig, use_container_width=True)

                # Tabela de dados recentes
                st.markdown("### 📋 Últimos pregões")
                df_display = pd.DataFrame(h.data[-20:])
                df_display["date"] = pd.to_datetime(df_display["date"]).dt.strftime(
                    "%Y-%m-%d"
                )
                df_display = df_display.rename(
                    columns={
                        "date": "Data",
                        "open": "Abertura",
                        "high": "Máxima",
                        "low": "Mínima",
                        "close": "Fechamento",
                        "volume": "Volume",
                    }
                )
                df_display["Volume"] = df_display["Volume"].apply(
                    lambda x: format_large_number(x)
                )
                st.dataframe(
                    df_display,
                    use_container_width=True,
                    hide_index=True,
                )

            except StockCollectorError as e:
                st.error(f"❌ {e}")
            except Exception as e:
                st.error(f"Erro inesperado: {e}")


def page_analyze():
    """Página de análise completa com IA."""
    st.markdown(
        '<div class="main-header">🤖 Análise IA</div>',
        unsafe_allow_html=True,
    )

    ticker = st.text_input(
        "Ticker da ação",
        placeholder="Ex: PETR4, VALE3, AAPL, MSFT",
        value=st.session_state.get("quick_ticker", ""),
        key="analyze_ticker_input",
    )

    exchange = st.selectbox(
        "Bolsa",
        ["Auto", "B3", "NYSE"],
        index=0,
        key="analyze_exchange",
    )

    if st.button("🔍 Analisar com IA", type="primary") and ticker:
        st.session_state["quick_ticker"] = ""
        with st.spinner(
            f"🤖 Coletando dados e gerando análise para {ticker.upper()}..."
        ):
            try:
                exch = None if exchange == "Auto" else exchange
                result = financial_agent.analyze(ticker.upper(), exch)

                q = result["quote"]

                st.markdown(
                    f'<h2 style="color: var(--accent-primary);">'
                    f"{format_ticker_display(q.ticker, q.exchange)}"
                    f"</h2>",
                    unsafe_allow_html=True,
                )

                # Cotação resumo
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    render_metric(
                        "Preço",
                        format_currency(q.price, q.currency),
                        q.change_percent,
                    )
                with col2:
                    render_metric(
                        "Variação",
                        format_change(q.change, q.change_percent),
                        q.change_percent,
                    )
                with col3:
                    render_metric("Empresa", q.name or "N/A")
                with col4:
                    render_metric("Bolsa", q.exchange)

                # Fundamentos
                fund = result.get("fundamentals")
                if fund:
                    st.markdown("### 📊 Fundamentos")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        render_metric("Setor", fund.sector or "N/A")
                    with col2:
                        render_metric(
                            "Market Cap", format_large_number(fund.market_cap)
                        )
                    with col3:
                        render_metric(
                            "P/L", f"{fund.pe_ratio:.2f}" if fund.pe_ratio else "N/A"
                        )
                    with col4:
                        render_metric(
                            "Dividend Yield",
                            format_percent(fund.dividend_yield)
                            if fund.dividend_yield
                            else "N/A",
                        )

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        render_metric(
                            "ROE",
                            format_percent(fund.roe) if fund.roe else "N/A",
                        )
                    with col2:
                        render_metric(
                            "P/VP",
                            f"{fund.pb_ratio:.2f}" if fund.pb_ratio else "N/A",
                        )
                    with col3:
                        render_metric(
                            "Beta", f"{fund.beta:.2f}" if fund.beta else "N/A"
                        )
                    with col4:
                        render_metric(
                            "Margem Líquida",
                            format_percent(fund.net_margin)
                            if fund.net_margin
                            else "N/A",
                        )

                # Análise IA
                analysis = result.get("analysis", "")
                if analysis and "não disponível" not in analysis.lower():
                    st.markdown("### 🤖 Análise da Inteligência Artificial")
                    st.markdown(
                        f'<div style="background: var(--ai-box-bg); border-radius: 10px; '
                        f'padding: 1.5rem; border: 1px solid var(--ai-box-border); '
                        f'line-height: 1.7;">{analysis}</div>',
                        unsafe_allow_html=True,
                    )
                elif analysis:
                    st.warning(f"⚠️ {analysis}")

            except StockCollectorError as e:
                st.error(f"❌ {e}")
            except Exception as e:
                st.error(f"Erro inesperado: {e}")


def page_compare():
    """Página de comparação de múltiplas ações."""
    st.markdown(
        '<div class="main-header">⚖️ Comparar Ações</div>',
        unsafe_allow_html=True,
    )

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
            index=2,
            key="compare_period",
        )
    with col2:
        pass

    if st.button("⚖️ Comparar", type="primary") and tickers_str:
        tickers = [t.strip().upper() for t in tickers_str.split(",") if t.strip()]

        if len(tickers) < 2:
            st.error("❌ Informe pelo menos 2 tickers para comparar.")
            return

        with st.spinner(f"Comparando {', '.join(tickers)}..."):
            try:
                result = financial_agent.compare(tickers)

                # Tabela comparativa
                st.markdown("### 📊 Tabela Comparativa")
                rows = []
                for q, f in zip(result["quotes"], result["fundamentals"]):
                    rows.append(
                        {
                            "Ticker": q.ticker,
                            "Bolsa": q.exchange,
                            "Preço": format_currency(q.price, q.currency),
                            "Variação": f"{q.change_percent:+.2f}%",
                            "P/L": f"{f.pe_ratio:.2f}" if f and f.pe_ratio else "N/A",
                            "DY": (
                                format_percent(f.dividend_yield)
                                if f and f.dividend_yield
                                else "N/A"
                            ),
                        }
                    )

                st.dataframe(
                    pd.DataFrame(rows),
                    use_container_width=True,
                    hide_index=True,
                )

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

                # Análise IA
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


def _render_watchlist_table(limit: Optional[int] = None):
    """Renderiza a tabela da watchlist (reutilizável)."""
    try:
        from stonks_ai.models.watchlist import WatchlistItem

        with db.session() as session:
            query = session.query(WatchlistItem).order_by(WatchlistItem.added_at.desc())
            if limit:
                query = query.limit(limit)
            items = query.all()

        if not items:
            st.info("📋 Watchlist vazia. Adicione tickers usando o formulário abaixo.")
            return

        rows = []
        for item in items:
            try:
                q = financial_agent.get_quote(item.ticker, item.exchange)
                rows.append(
                    {
                        "Ticker": q.ticker,
                        "Bolsa": item.exchange,
                        "Preço": format_currency(q.price, q.currency),
                        "Variação": f"{q.change_percent:+.2f}%",
                        "Alvo": (
                            format_currency(item.target_price, q.currency)
                            if item.target_price
                            else "-"
                        ),
                    }
                )
            except StockCollectorError:
                rows.append(
                    {
                        "Ticker": item.ticker,
                        "Bolsa": item.exchange,
                        "Preço": "Erro",
                        "Variação": "-",
                        "Alvo": "-",
                    }
                )

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

    except DatabaseError as e:
        st.error(f"❌ Erro no banco: {e}")
    except Exception as e:
        st.error(f"❌ Erro: {e}")


def page_watchlist():
    """Página de gerenciamento da watchlist."""
    st.markdown(
        '<div class="main-header">📋 Watchlist</div>',
        unsafe_allow_html=True,
    )

    tab1, tab2 = st.tabs(["📋 Minha Watchlist", "➕ Adicionar / ❌ Remover"])

    with tab1:
        _render_watchlist_table()

    with tab2:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### ➕ Adicionar Ticker")
            add_ticker = st.text_input(
                "Ticker",
                placeholder="Ex: PETR4",
                key="wl_add_ticker",
            )
            add_exchange = st.selectbox(
                "Bolsa",
                ["B3", "NYSE"],
                index=0,
                key="wl_add_exchange",
            )
            add_name = st.text_input(
                "Nome da watchlist",
                value="Minha Watchlist",
                key="wl_add_name",
            )
            add_target = st.number_input(
                "Preço alvo (opcional)",
                min_value=0.0,
                step=0.01,
                key="wl_add_target",
            )

            if st.button("✅ Adicionar", type="primary") and add_ticker:
                try:
                    from stonks_ai.models.watchlist import WatchlistItem

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
                from stonks_ai.models.watchlist import WatchlistItem

                with db.session() as session:
                    items = session.query(WatchlistItem).all()

                if items:
                    ticker_options = {
                        f"{item.ticker} ({item.exchange})": item.id
                        for item in items
                    }
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


def page_config():
    """Página de configuração do sistema."""
    st.markdown(
        '<div class="main-header">⚙️ Configuração</div>',
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3 = st.tabs(["📋 Visualizar", "✏️ Editar", "🛠️ Sistema"])

    with tab1:
        st.markdown("### Configuração Atual")
        import yaml

        config_yaml = yaml.dump(config.data, default_flow_style=False, allow_unicode=True)
        st.code(config_yaml, language="yaml")

    with tab2:
        st.markdown("### Alterar Configuração")

        col1, col2 = st.columns(2)
        with col1:
            llm_model = st.text_input(
                "Modelo LLM",
                value=config.get("llm", "model", default="llama3.2:3b"),
                key="cfg_llm_model",
            )
            llm_temp = st.slider(
                "Temperatura LLM",
                min_value=0.0,
                max_value=2.0,
                value=config.get("llm", "temperature", default=0.3),
                step=0.1,
                key="cfg_llm_temp",
            )
            llm_endpoint = st.text_input(
                "Endpoint Ollama",
                value=config.get("llm", "endpoint", default="http://localhost:11434"),
                key="cfg_llm_endpoint",
            )

        with col2:
            default_exchange = st.selectbox(
                "Bolsa padrão",
                ["B3", "NYSE"],
                index=0 if config.get("stocks", "default_exchange") == "B3" else 1,
                key="cfg_default_exchange",
            )
            language = st.selectbox(
                "Idioma",
                ["pt-BR", "en-US"],
                index=0 if config.get("app", "language") == "pt-BR" else 1,
                key="cfg_language",
            )

        if st.button("💾 Salvar Configuração", type="primary"):
            try:
                config.set(llm_model, "llm", "model")
                config.set(llm_temp, "llm", "temperature")
                config.set(llm_endpoint, "llm", "endpoint")
                config.set(default_exchange, "stocks", "default_exchange")
                config.set(language, "app", "language")
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
            if st.button("🔍 Verificar Conexão Ollama"):
                if financial_agent.check_llm_available():
                    st.success("✅ Ollama está online!")
                else:
                    st.warning(
                        "⚠️ Ollama não está rodando. Execute 'ollama serve' "
                        "no terminal para ativar."
                    )

            if st.button("🔍 Verificar Banco de Dados"):
                if db.health_check():
                    st.success(f"✅ Banco OK em: {db.db_path}")
                else:
                    st.error("❌ Banco de dados com problemas.")

        # Info do sistema
        st.markdown("### ℹ️ Informações do Sistema")
        info_col1, info_col2 = st.columns(2)
        with info_col1:
            st.markdown(f"**Versão:** {__version__}")
            st.markdown(f"**Banco:** {db.db_path}")
        with info_col2:
            st.markdown(f"**Config:** {config.config_path}")
            st.markdown(
                f"**LLM:** {config.get('llm', 'model', default='N/A')} "
                f"em {config.get('llm', 'endpoint', default='N/A')}"
            )


# ── Página de Chat Financeiro ─────────────────────────────────────────
def page_chat():
    """Página de chat financeiro com IA para tirar dúvidas gerais."""
    st.markdown(
        '<div class="main-header">💬 Chat Financeiro</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sub-header">'
        "Tire dúvidas sobre mercado financeiro, investimentos, "
        "indicadores, economia e mais"
        "</div>",
        unsafe_allow_html=True,
    )

    # Inicializa histórico da conversa na sessão
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
        st.session_state["chat_history"].append({
            "role": "assistant",
            "content": (
                "Olá! 👋 Sou o assistente financeiro do **Stonks AI**. "
                "Pode me perguntar sobre:\n\n"
                "• 📊 **Ações e mercado** — B3, NYSE, ETFs, FIIs\n"
                "• 📈 **Indicadores** — P/L, P/VP, ROE, Dividend Yield\n"
                "• 💰 **Estratégias** — Value investing, growth, dividendos\n"
                "• 🏦 **Economia** — Juros, inflação, câmbio, PIB\n"
                "• 📝 **Finanças pessoais** — Orçamento, reserva, planejamento\n\n"
                "**Como posso ajudar você hoje?** 🚀"
            ),
        })

    # Área de sugestões rápidas (só no início da conversa)
    user_msgs = [m for m in st.session_state["chat_history"] if m["role"] == "user"]
    if not user_msgs:
        st.markdown("### ⚡ Perguntas rápidas")
        quick_questions = [
            "O que é P/L e como interpretar?",
            "Qual a diferença entre CDB e Tesouro Direto?",
            "Como calcular dividend yield?",
            "O que é value investing?",
            "Como declarar ações no Imposto de Renda?",
            "O que é um ETF e como investir?",
        ]
        cols = st.columns(2)
        for i, question in enumerate(quick_questions):
            col = cols[i % 2]
            with col:
                if st.button(question, key=f"quick_q_{i}", use_container_width=True):
                    # Adiciona mensagem do usuário
                    st.session_state["chat_history"].append({
                        "role": "user",
                        "content": question,
                    })

                    # Gera resposta da IA imediatamente
                    try:
                        history_for_context = st.session_state["chat_history"][-10:]
                        response = financial_agent.chat(
                            message=question,
                            conversation_history=[
                                {"role": m["role"], "content": m["content"]}
                                for m in history_for_context
                                if m["role"] != "assistant" or m is not history_for_context[-1]
                            ],
                        )
                        st.session_state["chat_history"].append({
                            "role": "assistant",
                            "content": response,
                        })
                    except Exception as e:
                        st.session_state["chat_history"].append({
                            "role": "assistant",
                            "content": f"❌ **Erro ao processar sua pergunta:** {e}",
                        })

                    st.rerun()

        st.markdown("---")

    # Exibe histórico da conversa
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Input do usuário
    if prompt := st.chat_input(
        "Digite sua dúvida financeira...",
        key="chat_input",
    ):
        # Adiciona mensagem do usuário
        st.session_state["chat_history"].append({
            "role": "user",
            "content": prompt,
        })

        with st.chat_message("user"):
            st.markdown(prompt)

        # Gera resposta da IA
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("🤔 Pensando...")

            try:
                # Prepara histórico para contexto (últimas 10 mensagens)
                history_for_context = st.session_state["chat_history"][-10:]

                response = financial_agent.chat(
                    message=prompt,
                    conversation_history=[
                        {"role": m["role"], "content": m["content"]}
                        for m in history_for_context
                        if m["role"] != "assistant" or m is not history_for_context[-1]
                    ],
                )

                message_placeholder.markdown(response)
                st.session_state["chat_history"].append({
                    "role": "assistant",
                    "content": response,
                })

            except Exception as e:
                message_placeholder.markdown(
                    f"❌ **Erro ao processar sua pergunta:** {e}"
                )

        st.rerun()

    # Botão para limpar conversa
    if st.session_state["chat_history"]:
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🗑️ Limpar Conversa", use_container_width=True):
                st.session_state["chat_history"] = []
                st.rerun()


# ── Página: Finanças Pessoais ─────────────────────────────────────────
def page_finance():
    """Painel de finanças pessoais com dashboard, importação e transações."""
    st.markdown("## 💰 Finanças Pessoais")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard",
        "📥 Importar Extrato",
        "📝 Transações",
        "🏷️ Categorias",
    ])

    with tab1:
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

                # Top categories
                if summary["top_categories"]:
                    st.markdown("### 🏷️ Categorias com Mais Gastos")
                    cat_df = pd.DataFrame(summary["top_categories"])
                    st.dataframe(
                        cat_df[["name", "amount", "percent"]].rename(
                            columns={"name": "Categoria", "amount": "Valor (R$)", "percent": "%"}
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )

                # Active goals
                if data["active_goals"]:
                    st.markdown("### 🎯 Metas Ativas")
                    for g in data["active_goals"]:
                        pct = g.get("progress_percent", 0)
                        st.progress(min(pct / 100, 1.0))
                        st.caption(
                            f"{g['name']}: R$ {g['current_amount']:,.2f} / "
                            f"R$ {g['target_amount']:,.2f} ({pct:.1f}%)"
                        )

                # AI Summary
                if st.button("🤖 Gerar Resumo com IA"):
                    with st.spinner("Gerando análise..."):
                        ai_text = personal_finance_agent.get_monthly_summary_ai(year, month)
                        st.info(ai_text)

            except Exception as e:
                st.error(f"Erro ao carregar dashboard: {e}")

    with tab2:
        st.markdown("### 📥 Importar Extrato Bancário")
        st.markdown("Formatos suportados: **CSV**, **Excel** (.xlsx/.xls), **PDF**")

        uploaded_file = st.file_uploader(
            "Selecione o arquivo de extrato",
            type=["csv", "xlsx", "xls", "pdf"],
        )

        if uploaded_file is not None:
            # Save to temp file and import
            import tempfile
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

            # Cleanup
            import os
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    with tab3:
        st.markdown("### 📝 Transações Recentes")

        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filter_days = st.selectbox("Período", [7, 15, 30, 60, 90], index=1)
        with col_f2:
            filter_type = st.selectbox("Tipo", ["all", "expense", "income"])
        with col_f3:
            limit_n = st.number_input("Máximo", min_value=10, max_value=200, value=50)

        # ── Listagem de transações com ações ──────────────────────────
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

        # ── Diálogo de exclusão ──────────────────────────────────────
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

        # ── Formulário de edição ─────────────────────────────────────
        if "edit_tx_id" in st.session_state and st.session_state["edit_tx_id"]:
            tx_data = st.session_state.get("edit_tx_data", {})
            st.markdown("---")
            st.markdown(f"### ✏️ Editando Transação #{st.session_state['edit_tx_id']}")

            with st.form("edit_transaction"):
                edit_desc = st.text_input(
                    "Descrição",
                    value=tx_data.get("description", ""),
                )
                edit_amount = st.number_input(
                    "Valor",
                    min_value=0.01,
                    format="%.2f",
                    value=float(tx_data.get("amount", 0)),
                )
                edit_type = st.selectbox(
                    "Tipo",
                    ["expense", "income"],
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
                edit_cat = st.selectbox(
                    "Categoria",
                    [""] + cat_options,
                    index=cat_index,
                )

                # Parse date for display
                raw_date = tx_data.get("date", "")
                if hasattr(raw_date, "strftime"):
                    default_date_str = raw_date.strftime("%Y-%m-%d")
                else:
                    default_date_str = str(raw_date)[:10] if raw_date else ""

                edit_date = st.date_input(
                    "Data",
                    value=datetime.strptime(default_date_str, "%Y-%m-%d") if default_date_str else datetime.now(),
                )
                edit_notes = st.text_area(
                    "Observações",
                    value=tx_data.get("notes") or "",
                )

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

        # ── Add transaction form ─────────────────────────────────────
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

    with tab4:
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


# ── Página: Metas Financeiras ──────────────────────────────────────────
def page_goals():
    """Gerenciamento de metas financeiras."""
    st.markdown("## 🎯 Metas Financeiras")

    tab1, tab2 = st.tabs(["📋 Metas", "➕ Nova Meta"])

    with tab1:
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
                            # Linha principal: info + ações
                            col_info, col_contrib, col_actions = st.columns([2, 1, 1])

                            with col_info:
                                icon = g.get("icon", "🎯")
                                st.markdown(f"**{icon} {g['name']}**")
                                st.progress(min(pct / 100, 1.0))
                                st.caption(
                                    f"R$ {g['current_amount']:,.2f} / "
                                    f"R$ {g['target_amount']:,.2f} ({pct:.1f}%)"
                                )
                                # Detalhes extras
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
                                        label_visibility="collapsed", placeholder="R$"
                                    )
                                    if st.button("➕ Contribuir", key=f"btn_{goal_id}"):
                                        if contrib > 0:
                                            with st.spinner("Atualizando..."):
                                                try:
                                                    updated = personal_finance_agent.contribute_to_goal(
                                                        goal_id, contrib
                                                    )
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

        # ── Diálogo de exclusão ──────────────────────────────────────
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

        # ── Formulário de edição ─────────────────────────────────────
        if "edit_goal_id" in st.session_state and st.session_state["edit_goal_id"]:
            goal_data = st.session_state.get("edit_goal_data", {})
            st.markdown("---")
            st.markdown(f"### ✏️ Editando Meta: {goal_data.get('name', '')}")

            with st.form("edit_goal"):
                edit_name = st.text_input(
                    "Nome da Meta",
                    value=goal_data.get("name", ""),
                )
                edit_target = st.number_input(
                    "Valor Alvo (R$)",
                    min_value=0.01,
                    format="%.2f",
                    value=float(goal_data.get("target_amount", 0)),
                )

                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    raw_deadline = goal_data.get("deadline", "")
                    if hasattr(raw_deadline, "strftime"):
                        default_deadline = datetime.strptime(
                            raw_deadline.strftime("%Y-%m-%d"), "%Y-%m-%d"
                        )
                    elif raw_deadline:
                        default_deadline = datetime.strptime(str(raw_deadline)[:10], "%Y-%m-%d")
                    else:
                        default_deadline = None
                    edit_deadline = st.date_input(
                        "Prazo (opcional)",
                        value=default_deadline,
                    )
                with col_e2:
                    edit_goal_type = st.selectbox(
                        "Tipo",
                        ["savings", "debt", "investment", "custom"],
                        index=["savings", "debt", "investment", "custom"].index(
                            goal_data.get("goal_type", "savings")
                        ),
                    )

                col_e3, col_e4 = st.columns(2)
                with col_e3:
                    edit_priority = st.selectbox(
                        "Prioridade",
                        ["low", "medium", "high"],
                        index=["low", "medium", "high"].index(
                            goal_data.get("priority", "medium")
                        ),
                    )
                with col_e4:
                    edit_status = st.selectbox(
                        "Status",
                        ["active", "completed", "cancelled", "paused"],
                        index=["active", "completed", "cancelled", "paused"].index(
                            goal_data.get("status", "active")
                        ),
                    )

                edit_description = st.text_area(
                    "Descrição",
                    value=goal_data.get("description") or "",
                )

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

    with tab2:
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


# ── Página: Alertas Inteligentes ───────────────────────────────────────
def page_alerts():
    """Visualização e gerenciamento de alertas."""
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
                        "high": "🔴",
                        "medium": "🟡",
                        "low": "🟢",
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


# ── Router principal ────────────────────────────────────────────────────
def main():
    """Função principal que renderiza a aplicação."""
    render_sidebar()

    # Página padrão
    if "page" not in st.session_state:
        st.session_state["page"] = "dashboard"

    # Router
    pages = {
        "dashboard": page_dashboard,
        "chat": page_chat,
        "quote": page_quote,
        "history": page_history,
        "analyze": page_analyze,
        "compare": page_compare,
        "watchlist": page_watchlist,
        "finance": page_finance,
        "goals": page_goals,
        "alerts": page_alerts,
        "config": page_config,
    }

    current_page = st.session_state.get("page", "dashboard")
    page_func = pages.get(current_page, page_dashboard)
    page_func()


if __name__ == "__main__":
    main()
