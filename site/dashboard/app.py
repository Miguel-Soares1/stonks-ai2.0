"""
Stonks AI — Site Publico (Streamlit Cloud)
===========================================

Deploy gratuito no Streamlit Community Cloud.
Apenas cotacoes e analise de acoes — sem dados pessoais.

Uso:
    streamlit run site/dashboard/app.py
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from stonks_ai import __version__
from stonks_ai.agents.financial_agent import FinancialAgent
from stonks_ai.collectors.stocks.base import StockCollectorError
from stonks_ai.utils.formatters import (
    format_currency, format_large_number, format_percent, format_ticker_display,
)

# ── Configuracao da pagina ──────────────────────────────────────────────
st.set_page_config(
    page_title="Stonks AI — Análise de Ações B3 e NYSE",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Tema CSS ───────────────────────────────────────────────────────────
st.markdown("""
<style>
    :root {
        --bg-primary: #050508;
        --border: #1a1a2e;
        --border-accent: #1a3a2a;
    }
    .stApp {
        background: linear-gradient(180deg, #050508 0%, #0a0a12 50%, #050508 100%);
    }
    .main-header {
        font-size: 2.5rem; font-weight: 800; letter-spacing: -0.02em; margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem; color: #a0a0b0; margin-bottom: 2rem; line-height: 1.6;
    }
    .glass-card {
        background: rgba(17, 17, 24, 0.65); backdrop-filter: blur(20px);
        border: 1px solid #1a1a2e; border-radius: 20px; padding: 1.6rem;
        transition: all 0.3s ease;
    }
    .glass-card:hover {
        border-color: #1a3a2a; box-shadow: 0 0 32px rgba(0,200,83,0.08);
        transform: translateY(-2px);
    }
    .metric-card {
        background: rgba(17, 17, 24, 0.6); backdrop-filter: blur(12px);
        border: 1px solid #1a1a2e; border-radius: 16px; padding: 1.2rem;
        text-align: center; transition: all 0.3s ease;
    }
    .metric-card:hover {
        border-color: #1a3a2a; box-shadow: 0 4px 24px rgba(0,200,83,0.06);
        transform: translateY(-2px);
    }
    .metric-label {
        font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em;
        color: #606078; margin-bottom: 0.3rem; font-weight: 600;
    }
    .metric-value {
        font-size: 1.5rem; font-weight: 700; color: #e8e8ed;
    }
    .metric-value.positivo { color: #00c853; }
    .metric-value.negativo { color: #ff1744; }
    .ai-box {
        background: rgba(0,200,83,0.03); border: 1px solid rgba(0,200,83,0.1);
        border-radius: 16px; padding: 2rem; line-height: 1.8; font-size: 1.02rem;
    }
    .stButton > button {
        border-radius: 12px !important; font-weight: 600 !important;
        transition: all 0.3s ease !important; border: none !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #00c853, #00e676) !important;
        color: #000 !important; font-weight: 700 !important;
        box-shadow: 0 4px 20px rgba(0,200,83,0.15) !important;
    }
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 8px 32px rgba(0,200,83,0.25) !important; transform: translateY(-1px) !important;
    }
    .stButton > button[kind="secondary"] {
        background: rgba(255,255,255,0.04) !important; color: #e8e8ed !important;
        border: 1px solid #1a1a2e !important;
    }
    .stTextInput input {
        background: rgba(17,17,24,0.5) !important; border: 1px solid #1a1a2e !important;
        border-radius: 12px !important; color: #e8e8ed !important; padding: 12px 16px !important;
    }
    .stTextInput input:focus {
        border-color: #00c853 !important; box-shadow: 0 0 0 3px rgba(0,200,83,0.1) !important;
    }
    .stSelectbox > div > div {
        background: rgba(17,17,24,0.5) !important; backdrop-filter: blur(8px) !important;
        border: 1px solid #1a1a2e !important; border-radius: 12px !important;
    }
    .stSelectbox [data-baseweb="select"] [role="combobox"] {
        color: #e8e8ed !important; font-size: 0.95rem !important; padding: 8px 12px !important;
    }
    [data-testid="stSidebar"] {
        background: rgba(5,5,8,0.95); border-right: 1px solid #1a1a2e;
    }
    .premium-banner {
        background: linear-gradient(135deg, rgba(0,200,83,0.06), rgba(0,200,83,0.02));
        border: 1px solid rgba(0,200,83,0.15); border-radius: 16px;
        padding: 1.2rem 1.8rem; margin-top: 2rem;
    }
    .footer-site {
        text-align: center; padding: 2rem 0 0 0; margin-top: 3rem;
        border-top: 1px solid #1a1a2e; color: #606078; font-size: 0.82rem;
    }
    p, h1, h2, h3, span, label, li { color: #e8e8ed; }
</style>
""", unsafe_allow_html=True)


# ── Agente ──────────────────────────────────────────────────────────────
@st.cache_resource
def get_financial_agent() -> FinancialAgent:
    return FinancialAgent()


financial_agent = get_financial_agent()

# ── Estado da sessao ───────────────────────────────────────────────────
if "pagina" not in st.session_state:
    st.session_state["pagina"] = "inicio"


# ═══════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════
def renderizar_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 1.2rem;">
            <div style="font-size: 2rem;">🚀</div>
            <div style="font-size: 1.2rem; font-weight: 800;
                        background: linear-gradient(135deg, #00c853, #00e676);
                        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                        background-clip: text;">
                Stonks AI
            </div>
            <div style="font-size: 0.7rem; color: #606078; margin-top: 0.2rem;">
                Análise de Ações · Grátis
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(
            '<p style="font-size: 0.7rem; font-weight: 700; text-transform: uppercase; '
            'letter-spacing: 1px; color: #606078; margin-bottom: 0.3rem;">'
            '📍 Navegação</p>',
            unsafe_allow_html=True,
        )

        pagina_atual = st.session_state.get("pagina", "inicio")

        botoes = [
            ("🏠  Início", "inicio"),
            ("💲  Cotação", "cotacao"),
            ("🤖  Análise IA", "analise"),
            ("📈  Histórico", "historico"),
        ]

        for label, page_id in botoes:
            tipo = "primary" if pagina_atual == page_id else "secondary"
            if st.button(label, key=f"nav_{page_id}", use_container_width=True, type=tipo):
                st.session_state["pagina"] = page_id
                st.rerun()

        st.markdown("---")
        st.markdown(
            f'<p style="font-size: 0.7rem; color: #606078; text-align: center;">'
            f'🚀 Stonks AI v{__version__}<br>Open Source (MIT)</p>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════
# COMPONENTES
# ═══════════════════════════════════════════════════════════════════════

def cartao_metrica(rotulo: str, valor: str, variacao: float = None):
    css_class = ""
    if variacao is not None:
        css_class = "positivo" if variacao > 0 else ("negativo" if variacao < 0 else "")
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{rotulo}</div>
        <div class="metric-value {css_class}">{valor}</div>
    </div>
    """, unsafe_allow_html=True)


def banner_premium():
    st.markdown("""
    <div class="premium-banner">
        <span style="font-size: 0.95rem;">
            ⭐ <strong style="color: #00e676;">Premium</strong> —
            IA avançada, alertas de preço, dashboards personalizados.
            <strong>R$ 19/mês</strong>
        </span>
        <span style="font-size: 0.8rem; color: #606078;">🔜 Brevemente</span>
    </div>
    """, unsafe_allow_html=True)


def banner_afiliados():
    st.markdown("""
    <div style="background: rgba(255,255,255,0.02); border: 1px dashed #1a1a2e;
                border-radius: 12px; padding: 1rem 1.5rem; margin-top: 1.5rem;
                font-size: 0.88rem; color: #707080;">
        📊 <strong>Quer investir?</strong>
        Abra conta na <a href="https://rico.com.vc" target="_blank" style="color: #00c853;">Rico</a>,
        <a href="https://clear.com.br" target="_blank" style="color: #00c853;">Clear</a> ou
        <a href="https://xp.com.br" target="_blank" style="color: #00c853;">XP</a>
        com taxas reduzidas.
        <span style="color: #505060; font-size: 0.75rem;">(Links de afiliado)</span>
    </div>
    """, unsafe_allow_html=True)


def rodape():
    st.markdown(f"""
    <div class="footer-site">
        <p>🚀 <strong>Stonks AI</strong> · Open Source (MIT) ·
        <a href="https://github.com/miguel7p/stonks-ai" target="_blank" style="color: #00c853;">GitHub</a></p>
        <p style="font-size: 0.75rem; margin-top: 0.3rem;">
            ⚠️ Não somos consultores financeiros. As análises são informativas.
        </p>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# PAGINA: INICIO
# ═══════════════════════════════════════════════════════════════════════
def pagina_inicio():
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0 0.5rem;">
        <div style="display: inline-flex; align-items: center; gap: 8px;
                    padding: 5px 16px; background: rgba(0,200,83,0.08);
                    border: 1px solid #1a3a2a; border-radius: 50px;
                    font-size: 0.85rem; color: #00e676; margin-bottom: 1.5rem;">
            <span style="width: 7px; height: 7px; background: #00c853;
                         border-radius: 50%;"></span>
            Grátis · Sem Registo · Open Source
        </div>
        <h1 class="main-header">
            Análise de Ações com
            <span style="background: linear-gradient(135deg, #00c853, #00e676);
                         -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            Inteligência Artificial</span>
        </h1>
        <p class="sub-header">
            Cotações em tempo real da <strong>B3</strong> e <strong>NYSE/Nasdaq</strong>.
            Gráficos interativos. IA para análise técnica e fundamentalista.
            <strong style="color: #00e676;">Sem rastreamento. Sem cookies. Grátis.</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 💲 Cotação Rápida")
        ticker = st.text_input("Ticker da ação", placeholder="Ex: PETR4, AAPL, VALE3", key="inicio_ticker")
        exchange = st.selectbox("Bolsa", ["Auto", "B3", "NYSE"], key="inicio_exchange")
        if st.button("🔍 Buscar Cotação", type="primary", use_container_width=True) and ticker:
            st.session_state["ticker_cotacao"] = ticker.upper()
            st.session_state["exchange_cotacao"] = None if exchange == "Auto" else exchange
            st.session_state["pagina"] = "cotacao"
            st.rerun()

    with col2:
        st.markdown("### 🤖 Análise com IA")
        ticker2 = st.text_input("Ticker da ação", placeholder="Ex: VALE3, MSFT, ITUB4", key="inicio_analise")
        exchange2 = st.selectbox("Bolsa", ["Auto", "B3", "NYSE"], key="inicio_analise_exchange")
        if st.button("🤖 Analisar com IA", type="primary", use_container_width=True) and ticker2:
            st.session_state["ticker_analise"] = ticker2.upper()
            st.session_state["exchange_analise"] = None if exchange2 == "Auto" else exchange2
            st.session_state["pagina"] = "analise"
            st.rerun()

    st.markdown("---")
    st.markdown("### ✨ O que oferecemos")
    f1, f2, f3 = st.columns(3)
    with f1:
        st.markdown("""
        <div class="glass-card">
            <div style="font-size: 2.2rem; margin-bottom: 0.8rem;">📊</div>
            <h3 style="margin: 0 0 0.4rem 0;">Cotações em Tempo Real</h3>
            <p style="color: #a0a0b0; font-size: 0.9rem; margin: 0;">
                B3 e NYSE/Nasdaq. Preço, variação, volume, máxima e mínima do dia.
            </p>
        </div>
        """, unsafe_allow_html=True)
    with f2:
        st.markdown("""
        <div class="glass-card">
            <div style="font-size: 2.2rem; margin-bottom: 0.8rem;">🤖</div>
            <h3 style="margin: 0 0 0.4rem 0;">Análise com IA</h3>
            <p style="color: #a0a0b0; font-size: 0.9rem; margin: 0;">
                Análise técnica e fundamentalista automática com inteligência artificial.
            </p>
        </div>
        """, unsafe_allow_html=True)
    with f3:
        st.markdown("""
        <div class="glass-card">
            <div style="font-size: 2.2rem; margin-bottom: 0.8rem;">🛡️</div>
            <h3 style="margin: 0 0 0.4rem 0;">Privacidade Total</h3>
            <p style="color: #a0a0b0; font-size: 0.9rem; margin: 0;">
                Zero cookies. Zero rastreamento. Zero partilha de dados com terceiros.
            </p>
        </div>
        """, unsafe_allow_html=True)

    banner_premium()
    banner_afiliados()
    rodape()


# ═══════════════════════════════════════════════════════════════════════
# PAGINA: COTACAO
# ═══════════════════════════════════════════════════════════════════════
def pagina_cotacao():
    st.markdown('<h1 class="main-header">💲 Cotação</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Consulte o preço atual de qualquer ação da B3 ou NYSE.</p>',
                unsafe_allow_html=True)

    col1, col2, col3 = st.columns([3, 2, 2])
    with col1:
        ticker = st.text_input("Ticker", value=st.session_state.get("ticker_cotacao", ""),
                               placeholder="Ex: PETR4, AAPL", key="cotacao_input")
    with col2:
        exchange = st.selectbox("Bolsa", ["Auto", "B3", "NYSE"], key="cotacao_exchange")
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        pesquisar = st.button("🔍 Buscar", type="primary", use_container_width=True)

    if pesquisar and ticker:
        st.session_state["ticker_cotacao"] = ticker.upper()
        _mostrar_cotacao(ticker.upper(), None if exchange == "Auto" else exchange)
    elif st.session_state.get("ticker_cotacao"):
        _mostrar_cotacao(st.session_state["ticker_cotacao"],
                         st.session_state.get("exchange_cotacao"))

    banner_afiliados()
    rodape()


def _mostrar_cotacao(ticker: str, exchange=None):
    try:
        q = financial_agent.get_quote(ticker, exchange)
        st.markdown(f"""
        <h2 style="margin-bottom: 1rem;">
            {format_ticker_display(q.ticker, q.exchange)}
            <span style="font-size: 0.8rem; color: #606078; margin-left: 0.5rem;">
                {q.exchange}
            </span>
        </h2>
        """, unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        with c1: cartao_metrica("Preço", format_currency(q.price, q.currency), q.change_percent)
        with c2: cartao_metrica("Variação", f"{q.change_percent:+.2f}%", q.change_percent)
        with c3: cartao_metrica("Máxima", format_currency(q.high, q.currency))
        with c4: cartao_metrica("Mínima", format_currency(q.low, q.currency))

        c1, c2, c3, c4 = st.columns(4)
        with c1: cartao_metrica("Abertura", format_currency(q.open_price, q.currency))
        with c2: cartao_metrica("Fecho Anterior", format_currency(q.previous_close, q.currency))
        with c3: cartao_metrica("Volume", format_large_number(q.volume))
        with c4: cartao_metrica("Empresa", q.name or "N/A")

        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🤖 Analisar com IA", type="primary", use_container_width=True):
                st.session_state["ticker_analise"] = q.ticker
                st.session_state["exchange_analise"] = q.exchange
                st.session_state["pagina"] = "analise"
                st.rerun()
        with col_b:
            if st.button("📈 Ver Gráfico", use_container_width=True):
                st.session_state["ticker_historico"] = q.ticker
                st.session_state["exchange_historico"] = q.exchange
                st.session_state["pagina"] = "historico"
                st.rerun()

    except StockCollectorError as e:
        st.error(f"❌ {e}")
    except Exception as e:
        st.error(f"Erro inesperado: {e}")


# ═══════════════════════════════════════════════════════════════════════
# PAGINA: ANALISE IA
# ═══════════════════════════════════════════════════════════════════════
def pagina_analise():
    st.markdown('<h1 class="main-header">🤖 Análise com IA</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Análise técnica e fundamentalista automática com IA.</p>',
                unsafe_allow_html=True)

    ticker = st.text_input("Ticker", value=st.session_state.get("ticker_analise", ""),
                           placeholder="Ex: PETR4, VALE3, AAPL", key="analise_input")
    exchange = st.selectbox("Bolsa", ["Auto", "B3", "NYSE"], key="analise_exchange")

    if st.button("🔍 Analisar com IA", type="primary") and ticker:
        st.session_state["ticker_analise"] = ticker.upper()
        exch = None if exchange == "Auto" else exchange

        with st.spinner(f"🤖 A analisar {ticker.upper()}..."):
            try:
                resultado = financial_agent.analyze(ticker.upper(), exch)
                q = resultado["quote"]

                st.markdown(f"""
                <h2>{format_ticker_display(q.ticker, q.exchange)}</h2>
                """, unsafe_allow_html=True)

                c1, c2, c3 = st.columns(3)
                with c1: cartao_metrica("Preço", format_currency(q.price, q.currency), q.change_percent)
                with c2: cartao_metrica("Variação", f"{q.change_percent:+.2f}%", q.change_percent)
                with c3: cartao_metrica("Empresa", q.name or "N/A")

                fund = resultado.get("fundamentals")
                if fund:
                    st.markdown("### 📊 Fundamentos")
                    fc1, fc2, fc3, fc4 = st.columns(4)
                    with fc1: cartao_metrica("P/L", f"{fund.pe_ratio:.2f}" if fund.pe_ratio else "N/A")
                    with fc2: cartao_metrica("DY", format_percent(fund.dividend_yield) if fund.dividend_yield else "N/A")
                    with fc3: cartao_metrica("ROE", format_percent(fund.roe) if fund.roe else "N/A")
                    with fc4: cartao_metrica("Setor", fund.sector or "N/A")

                analise = resultado.get("analysis", "")
                if analise and "não disponível" not in analise.lower():
                    st.markdown("### 🤖 Análise da Inteligência Artificial")
                    st.markdown(f'<div class="ai-box">{analise}</div>', unsafe_allow_html=True)
                elif analise:
                    st.warning(f"⚠️ {analise}")

            except StockCollectorError as e:
                st.error(f"❌ {e}")
            except Exception as e:
                st.error(f"Erro inesperado: {e}")

    banner_premium()
    banner_afiliados()
    rodape()


# ═══════════════════════════════════════════════════════════════════════
# PAGINA: HISTORICO
# ═══════════════════════════════════════════════════════════════════════
def pagina_historico():
    st.markdown('<h1 class="main-header">📈 Histórico de Preços</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Gráfico interativo de velas (candlestick) com volume.</p>',
                unsafe_allow_html=True)

    ticker = st.text_input("Ticker", value=st.session_state.get("ticker_historico", ""),
                           placeholder="Ex: PETR4, AAPL", key="historico_input")

    c1, c2 = st.columns(2)
    with c1:
        exchange = st.selectbox("Bolsa", ["Auto", "B3", "NYSE"], key="historico_exchange")
    with c2:
        period = st.selectbox("Período", ["1 mês", "3 meses", "6 meses", "1 ano", "2 anos", "5 anos"],
                              index=2, key="historico_periodo")

    if st.button("📊 Gerar Gráfico", type="primary") and ticker:
        st.session_state["ticker_historico"] = ticker.upper()
        exch = None if exchange == "Auto" else exchange
        period_map = {"1 mês": "1mo", "3 meses": "3mo", "6 meses": "6mo",
                      "1 ano": "1y", "2 anos": "2y", "5 anos": "5y"}

        with st.spinner(f"A carregar histórico de {ticker.upper()}..."):
            try:
                h = financial_agent.get_history(ticker.upper(), exch,
                                                period=period_map.get(period, "6mo"))
                if not h.data:
                    st.warning(f"⚠️ Sem dados para {ticker} no período selecionado.")
                    return

                df = pd.DataFrame(h.data)
                df["date"] = pd.to_datetime(df["date"])

                fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                    vertical_spacing=0.03, row_heights=[0.7, 0.3])

                fig.add_trace(go.Candlestick(
                    x=df["date"], open=df["open"], high=df["high"],
                    low=df["low"], close=df["close"], name=ticker.upper(),
                    increasing_line_color="#00c853", decreasing_line_color="#ff1744",
                ), row=1, col=1)

                colors_vol = ["#00c853" if df["close"].iloc[i] >= df["open"].iloc[i]
                              else "#ff1744" for i in range(len(df))]
                fig.add_trace(go.Bar(x=df["date"], y=df["volume"],
                                     name="Volume", marker_color=colors_vol,
                                     opacity=0.5), row=2, col=1)

                fig.update_layout(
                    template="plotly_dark", height=500, showlegend=False,
                    margin=dict(l=20, r=20, t=30, b=20),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    xaxis_rangeslider_visible=False,
                )
                fig.update_yaxes(title_text="Preço", row=1, col=1)
                fig.update_yaxes(title_text="Volume", row=2, col=1)

                first, last = h.data[0], h.data[-1]
                pct = ((last["close"] - first["close"]) / first["close"] * 100) if first["close"] else 0
                avg = sum(d["close"] for d in h.data) / len(h.data)

                mc1, mc2, mc3, mc4 = st.columns(4)
                with mc1: cartao_metrica("Período", f"{first['date'][:10]} → {last['date'][:10]}")
                with mc2: cartao_metrica("Variação", f"{pct:+.2f}%", pct)
                with mc3: cartao_metrica("Média", f"{avg:.2f}")
                with mc4: cartao_metrica("Fecho Atual", f"{last['close']:.2f}", pct)

                st.plotly_chart(fig, use_container_width=True)

            except StockCollectorError as e:
                st.error(f"❌ {e}")
            except Exception as e:
                st.error(f"Erro inesperado: {e}")

    banner_afiliados()
    rodape()


# ═══════════════════════════════════════════════════════════════════════
# ROUTER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════
renderizar_sidebar()

PAGINAS = {
    "inicio": pagina_inicio,
    "cotacao": pagina_cotacao,
    "analise": pagina_analise,
    "historico": pagina_historico,
}

pagina_atual = st.session_state.get("pagina", "inicio")
PAGINAS.get(pagina_atual, pagina_inicio)()
