"""
Coletor de dados da B3 (Brasil) usando yfinance.

Tickers brasileiros no yfinance usam sufixo .SA (ex: PETR4.SA, VALE3.SA, ITUB4.SA).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import yfinance as yf
import pandas as pd

from stonks_ai.collectors.stocks.base import (
    BaseStockCollector,
    StockCollectorError,
    StockFundamentals,
    StockHistory,
    StockQuote,
)
from stonks_ai.config import config


class B3Collector(BaseStockCollector):
    """Coletor de dados da B3 (Bolsa do Brasil)."""

    def __init__(self):
        super().__init__(exchange="B3")
        self._suffix = config.get("stocks", "b3_suffix", default=".SA")

    def _format_ticker(self, ticker: str) -> str:
        """Garante que o ticker tenha o sufixo .SA para yfinance."""
        ticker = ticker.strip().upper()
        if not ticker.endswith(".SA"):
            ticker += self._suffix
        return ticker

    def _get_ticker_obj(self, ticker: str) -> yf.Ticker:
        """Obtém objeto Ticker do yfinance com validação."""
        formatted = self._format_ticker(ticker)
        try:
            obj = yf.Ticker(formatted)
            # Testa se o ticker existe (tenta acessar info)
            info = obj.info
            if not info or (info.get("regularMarketPrice") is None and info.get("currentPrice") is None):
                # Pode ser que o ticker não exista - verifica com uma chamada rápida
                hist = obj.history(period="1d")
                if hist.empty:
                    raise StockCollectorError(
                        f"STK-001: Ticker '{ticker}' não encontrado na B3. "
                        f"Verifique o código (ex: PETR4, VALE3, ITUB4)"
                    )
            return obj
        except StockCollectorError:
            raise
        except Exception as e:
            err_str = str(e).lower()
            if "rate" in err_str and ("limit" in err_str or "429" in err_str):
                raise StockCollectorError(
                    f"STK-005: Limite de requisições excedido. "
                    f"Aguarde 60 segundos antes de nova consulta."
                )
            raise StockCollectorError(
                f"STK-003: Não foi possível conectar ao Yahoo Finance. "
                f"Verifique sua conexão de internet. Detalhes: {e}"
            )

    def get_quote(self, ticker: str) -> StockQuote:
        """Obtém cotação atual de uma ação da B3."""
        if not self.validate_ticker(ticker):
            raise StockCollectorError(
                f"STK-001: Ticker inválido: '{ticker}'"
            )

        obj = self._get_ticker_obj(ticker)
        info = obj.info

        try:
            price = info.get("regularMarketPrice") or info.get("currentPrice") or 0.0
            prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose") or 0.0
            change = price - prev_close
            change_percent = (change / prev_close * 100) if prev_close else 0.0

            return StockQuote(
                ticker=ticker.strip().upper(),
                exchange="B3",
                price=price,
                change=round(change, 2),
                change_percent=round(change_percent, 2),
                high=info.get("regularMarketDayHigh") or info.get("dayHigh") or 0.0,
                low=info.get("regularMarketDayLow") or info.get("dayLow") or 0.0,
                open_price=info.get("regularMarketOpen") or info.get("open") or 0.0,
                previous_close=prev_close,
                volume=info.get("regularMarketVolume") or info.get("volume") or 0,
                currency="BRL",
                name=info.get("longName") or info.get("shortName") or ticker,
            )
        except (KeyError, TypeError, ValueError) as e:
            raise StockCollectorError(
                f"STK-004: Erro ao processar dados do ticker '{ticker}': {e}"
            )

    def get_history(
        self,
        ticker: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> StockHistory:
        """Obtém dados históricos de uma ação da B3.

        Períodos válidos: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        Intervalos válidos: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
        """
        if not self.validate_ticker(ticker):
            raise StockCollectorError(f"STK-001: Ticker inválido: '{ticker}'")

        formatted = self._format_ticker(ticker)
        try:
            df = yf.download(formatted, period=period, interval=interval, progress=False)

            if df.empty:
                raise StockCollectorError(
                    f"STK-004: Nenhum dado histórico disponível para {ticker} "
                    f"no período selecionado."
                )

            # Achata colunas MultiIndex (ex: ('Close', 'PETR4.SA')) se necessário
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Converte DataFrame para lista de dicionários
            records = []
            for idx, row in df.iterrows():
                timestamp = idx.isoformat() if hasattr(idx, "isoformat") else str(idx)
                records.append({
                    "date": timestamp,
                    "open": round(float(row["Open"]), 2) if pd.notna(row.get("Open")) else 0.0,
                    "high": round(float(row["High"]), 2) if pd.notna(row.get("High")) else 0.0,
                    "low": round(float(row["Low"]), 2) if pd.notna(row.get("Low")) else 0.0,
                    "close": round(float(row["Close"]), 2) if pd.notna(row.get("Close")) else 0.0,
                    "volume": int(row["Volume"]) if pd.notna(row.get("Volume")) else 0,
                })

            return StockHistory(
                ticker=ticker.strip().upper(),
                exchange="B3",
                period=period,
                interval=interval,
                data=records,
            )
        except StockCollectorError:
            raise
        except Exception as e:
            err_str = str(e).lower()
            if "rate" in err_str and ("limit" in err_str or "429" in err_str):
                raise StockCollectorError(
                    f"STK-005: Limite de requisições excedido. "
                    f"Aguarde 60 segundos antes de nova consulta."
                )
            raise StockCollectorError(
                f"STK-003: Erro ao obter histórico: {e}"
            )

    def get_fundamentals(self, ticker: str) -> Optional[StockFundamentals]:
        """Obtém dados fundamentalistas de uma ação da B3."""
        if not self.validate_ticker(ticker):
            raise StockCollectorError(f"STK-001: Ticker inválido: '{ticker}'")

        try:
            obj = self._get_ticker_obj(ticker)
            info = obj.info

            if not info or info.get("marketCap") is None:
                return None

            return StockFundamentals(
                ticker=ticker.strip().upper(),
                name=info.get("longName") or info.get("shortName") or "",
                sector=info.get("sector") or info.get("industry") or "N/A",
                market_cap=info.get("marketCap") or 0,
                pe_ratio=info.get("trailingPE") or info.get("forwardPE"),
                dividend_yield=info.get("dividendYield"),
                eps=info.get("trailingEps"),
                beta=info.get("beta"),
                pb_ratio=info.get("priceToBook"),
                roe=info.get("returnOnEquity"),
                net_margin=info.get("profitMargins"),
                debt_equity=info.get("debtToEquity"),
                revenue=info.get("totalRevenue"),
                net_income=info.get("netIncomeToCommon"),
                free_cash_flow=info.get("freeCashflow"),
                currency="BRL",
            )
        except StockCollectorError:
            raise
        except Exception as e:
            raise StockCollectorError(
                f"STK-009: Dados fundamentalistas indisponíveis para {ticker}: {e}"
            )
