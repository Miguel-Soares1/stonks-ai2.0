"""Modelo de histórico de consultas de ações."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from stonks_ai.database import Base


class StockQueryHistory(Base):
    """Registro histórico de consultas de ações feitas pelo usuário."""

    __tablename__ = "stock_query_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False, index=True)
    exchange = Column(String(10), nullable=False)
    query_type = Column(String(50), nullable=False)  # quote, history, analysis, etc.
    result_summary = Column(Text, nullable=True)
    queried_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self) -> str:
        return f"<StockQueryHistory(ticker='{self.ticker}', type='{self.query_type}')>"
