"""Modelo de watchlist de ações."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String

from stonks_ai.database import Base


class WatchlistItem(Base):
    """Item da watchlist de ações do usuário."""

    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, default="Minha Watchlist")
    ticker = Column(String(20), nullable=False, index=True)
    exchange = Column(String(10), nullable=False, default="B3")
    target_price = Column(Float, nullable=True)
    notes = Column(String(500), nullable=True)
    added_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self) -> str:
        return f"<WatchlistItem(ticker='{self.ticker}', exchange='{self.exchange}')>"
