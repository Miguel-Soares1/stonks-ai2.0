"""
Métricas e cards reutilizáveis para a UI.
"""

from typing import Optional

import streamlit as st


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
