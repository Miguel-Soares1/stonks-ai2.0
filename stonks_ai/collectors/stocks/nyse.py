"""
Coletor de dados da NYSE e Nasdaq usando yfinance.

Tickers americanos são usados diretamente (ex: AAPL, MSFT, GOOGL).
"""

from typing import Optional

import yfinance as yf
import pandas as pd

from stonks_ai.collectors.stocks.base import (
    BaseStockCollector,
    StockCollectorError,
    StockFundamentals,
    StockHistory,
    StockQuote,
)


class NYSECollector(BaseStockCollector):
    """Coletor de dados da NYSE e Nasdaq (EUA)."""

    # Lista de sufixos comuns de tickers brasileiros
    BR_SUFFIXES = [".SA", ".BF"]

    def __init__(self):
        super().__init__(exchange="NYSE")

    @staticmethod
    def _is_brazilian_ticker(ticker: str) -> bool:
        """Verifica se o ticker parece ser brasileiro."""
        ticker_upper = ticker.strip().upper()
        for suffix in NYSECollector.BR_SUFFIXES:
            if ticker_upper.endswith(suffix):
                return True
        # Padrão comum brasileiro: 4 letras + 1 número (ex: PETR4, VALE3)
        if len(ticker_upper) == 5 and ticker_upper[:4].isalpha() and ticker_upper[4].isdigit():
            return True
        # Padrão brasileiro: 4 letras + 2 números (ex: TAEE11, LOGG3, B3SA3)
        if len(ticker_upper) == 6 and ticker_upper[:4].isalpha() and ticker_upper[4:].isdigit():
            return True
        return False

    def _get_ticker_obj(self, ticker: str) -> yf.Ticker:
        """Obtém objeto Ticker do yfinance com validação."""
        formatted = ticker.strip().upper()
        try:
            obj = yf.Ticker(formatted)
            info = obj.info
            if not info or (info.get("regularMarketPrice") is None and info.get("currentPrice") is None):
                hist = obj.history(period="1d")
                if hist.empty:
                    raise StockCollectorError(
                        f"STK-007: Ticker '{ticker}' não encontrado na NYSE ou Nasdaq."
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
                f"STK-010: Não foi possível conectar ao Yahoo Finance. "
                f"Verifique sua conexão de internet. Detalhes: {e}"
            )

    def get_quote(self, ticker: str) -> StockQuote:
        """Obtém cotação atual de uma ação da NYSE/Nasdaq."""
        if not self.validate_ticker(ticker):
            raise StockCollectorError(f"STK-007: Ticker inválido: '{ticker}'")

        # Verifica se o ticker parece brasileiro
        if self._is_brazilian_ticker(ticker):
            raise StockCollectorError(
                f"STK-008: Ticker '{ticker}' parece ser brasileiro. "
                f"Use o módulo B3 ou o comando 'stonks b3 {ticker}'"
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
                exchange="NYSE",
                price=price,
                change=round(change, 2),
                change_percent=round(change_percent, 2),
                high=info.get("regularMarketDayHigh") or info.get("dayHigh") or 0.0,
                low=info.get("regularMarketDayLow") or info.get("dayLow") or 0.0,
                open_price=info.get("regularMarketOpen") or info.get("open") or 0.0,
                previous_close=prev_close,
                volume=info.get("regularMarketVolume") or info.get("volume") or 0,
                currency="USD",
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
        """Obtém dados históricos de uma ação da NYSE/Nasdaq."""
        if not self.validate_ticker(ticker):
            raise StockCollectorError(f"STK-007: Ticker inválido: '{ticker}'")

        if self._is_brazilian_ticker(ticker):
            raise StockCollectorError(
                f"STK-008: Ticker '{ticker}' parece ser brasileiro. "
                f"Use o módulo B3."
            )

        formatted = ticker.strip().upper()
        try:
            df = yf.download(formatted, period=period, interval=interval, progress=False)

            if df.empty:
                raise StockCollectorError(
                    f"STK-004: Nenhum dado histórico disponível para {ticker} "
                    f"no período selecionado."
                )

            # Achata colunas MultiIndex (ex: ('Close', 'AAPL')) se necessário
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

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
                exchange="NYSE",
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
                f"STK-010: Erro ao obter histórico: {e}"
            )

    def get_fundamentals(self, ticker: str) -> Optional[StockFundamentals]:
        """Obtém dados fundamentalistas de uma ação da NYSE/Nasdaq."""
        if not self.validate_ticker(ticker):
            raise StockCollectorError(f"STK-007: Ticker inválido: '{ticker}'")

        if self._is_brazilian_ticker(ticker):
            raise StockCollectorError(
                f"STK-008: Ticker '{ticker}' parece ser brasileiro."
            )

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
                currency="USD",
            )
        except StockCollectorError:
            raise
        except Exception as e:
            raise StockCollectorError(
                f"STK-009: Dados fundamentalistas indisponíveis para {ticker}: {e}"
            )
