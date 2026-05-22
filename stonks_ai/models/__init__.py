"""Modelos ORM SQLAlchemy para persistência local (SQLite).

Exporta todas as classes de modelo e a lista __all_models__ para
inicialização do schema no database.py.
"""

from stonks_ai.models.user_preferences import UserPreference
from stonks_ai.models.watchlist import WatchlistItem
from stonks_ai.models.stock_history import StockQueryHistory
from stonks_ai.models.category import Category
from stonks_ai.models.transaction import Transaction
from stonks_ai.models.financial_goal import FinancialGoal
from stonks_ai.models.alert import Alert, AlertConfig

# Lista usada pelo database.initialize() para criar todas as tabelas
__all_models__ = [
    UserPreference,
    WatchlistItem,
    StockQueryHistory,
    Category,
    Transaction,
    FinancialGoal,
    Alert,
    AlertConfig,
]

__all__ = [
    "UserPreference",
    "WatchlistItem",
    "StockQueryHistory",
    "Category",
    "Transaction",
    "FinancialGoal",
    "Alert",
    "AlertConfig",
]
