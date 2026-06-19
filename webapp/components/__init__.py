"""
Componentes partilhados da interface web Stonks AI.
"""

from webapp.components.metrics import color_for_change, render_metric, render_info_box
from webapp.components.charts import build_price_chart, build_comparison_chart
from webapp.components.sidebar import render_sidebar, NAV_ITEMS

__all__ = [
    "color_for_change",
    "render_metric",
    "render_info_box",
    "build_price_chart",
    "build_comparison_chart",
    "render_sidebar",
    "NAV_ITEMS",
]
