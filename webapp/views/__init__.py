"""
Páginas da interface web do Stonks AI.

Cada módulo contém uma página completa (função page_*).
"""

from webapp.views.dashboard import page_dashboard
from webapp.views.chat import page_chat
from webapp.views.quote import page_quote
from webapp.views.history import page_history
from webapp.views.analyze import page_analyze
from webapp.views.compare import page_compare
from webapp.views.watchlist import page_watchlist
from webapp.views.finance import page_finance
from webapp.views.goals import page_goals
from webapp.views.alerts import page_alerts
from webapp.views.config import page_config

PAGE_REGISTRY = {
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

__all__ = [
    "page_dashboard",
    "page_chat",
    "page_quote",
    "page_history",
    "page_analyze",
    "page_compare",
    "page_watchlist",
    "page_finance",
    "page_goals",
    "page_alerts",
    "page_config",
    "PAGE_REGISTRY",
]
