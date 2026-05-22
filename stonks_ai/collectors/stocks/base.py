"""Classe base para coletores de dados do mercado de ações."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class StockQuote:
    """Dados de cotação de uma ação."""
    ticker: str
    exchange: str
    price: float
    change: float
    change_percent: float
    high: float
    low: float
    open_price: float
    previous_close: float
    volume: int
    currency: str = "BRL"
    name: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StockHistory:
    """Dados históricos de uma ação."""
    ticker: str
    exchange: str
    period: str
    interval: str
    data: List[Dict[str, Any]]
    currency: str = "BRL"


@dataclass
class StockFundamentals:
    """Dados fundamentalistas de uma ação."""
    ticker: str
    name: str
    sector: str
    market_cap: float
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    eps: Optional[float] = None
    beta: Optional[float] = None
    pb_ratio: Optional[float] = None
    roe: Optional[float] = None
    net_margin: Optional[float] = None
    debt_equity: Optional[float] = None
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    free_cash_flow: Optional[float] = None
    currency: str = "BRL"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StockCollectorError(Exception):
    """Erro base para coletores de dados de ações."""
    pass


class BaseStockCollector(ABC):
    """Classe base abstrata para coletores de dados do mercado de ações."""

    def __init__(self, exchange: str):
        self.exchange = exchange

    @abstractmethod
    def get_quote(self, ticker: str) -> StockQuote:
        """Obtém cotação atual de uma ação."""
        pass

    @abstractmethod
    def get_history(
        self,
        ticker: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> StockHistory:
        """Obtém dados históricos de uma ação."""
        pass

    @abstractmethod
    def get_fundamentals(self, ticker: str) -> Optional[StockFundamentals]:
        """Obtém dados fundamentalistas de uma ação."""
        pass

    def validate_ticker(self, ticker: str) -> bool:
        """Valida formato básico do ticker."""
        if not ticker or not isinstance(ticker, str):
            return False
        return len(ticker.strip()) >= 1
