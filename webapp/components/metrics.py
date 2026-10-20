"""
Métricas e cards reutilizáveis para a UI.
"""

from typing import Optional

import streamlit as st

from stonks_ai.utils.finance_utils import get_month_summary
from stonks_ai.utils.formatters import format_currency


def previous_month_summary(year: int, month: int) -> Optional[dict]:
    """Retorna o resumo do mês anterior, ou None se indisponível."""
    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    try:
        return get_month_summary(prev_year, prev_month)
    except Exception:
        return None


def delta_vs_previous(current: float, previous: Optional[dict], key: str) -> Optional[str]:
    """Formata a variação de um valor em relação ao mês anterior (para st.metric)."""
    if not previous or not previous.get("transaction_count"):
        return None
    diff = current - previous.get(key, 0)
    if abs(diff) < 0.005:
        return None
    sign = "+" if diff > 0 else "-"
    return f"{sign}{format_currency(abs(diff))} vs. mês anterior"


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
