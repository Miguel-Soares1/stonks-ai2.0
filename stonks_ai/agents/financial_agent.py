"""
Agente de análise financeira.

Combina dados de mercado com IA local para gerar análises completas de ações.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from stonks_ai.agents.base_agent import AgentError, BaseAgent
from stonks_ai.collectors.stocks.b3 import B3Collector
from stonks_ai.collectors.stocks.base import (
    StockCollectorError,
    StockFundamentals,
    StockHistory,
    StockQuote,
)
from stonks_ai.collectors.stocks.fundamental_data import FundamentalDataCollector
from stonks_ai.collectors.stocks.nyse import NYSECollector
from stonks_ai.config import config
from stonks_ai.llm.prompts import (
    FINANCIAL_ANALYSIS_SYSTEM_PROMPT,
    FINANCIAL_COMPARISON_PROMPT,
    format_stock_analysis_prompt,
)
from stonks_ai.models.stock_history import StockQueryHistory
from stonks_ai.utils.validators import detect_exchange


class FinancialAgent(BaseAgent):
    """Agente especializado em análise de ações e mercado financeiro."""

    def __init__(self):
        super().__init__()
        self.b3 = B3Collector()
        self.nyse = NYSECollector()
        self.fundamentus = FundamentalDataCollector()

    def get_collector(self, exchange: str):
        """Retorna o coletor apropriado para a bolsa."""
        if exchange.upper() == "B3":
            return self.b3
        elif exchange.upper() in ("NYSE", "NASDAQ"):
            return self.nyse
        else:
            raise ValueError(f"Exchange não suportada: {exchange}")

    def get_quote(self, ticker: str, exchange: Optional[str] = None) -> StockQuote:
        """Obtém cotação de uma ação."""
        if exchange is None:
            exchange = detect_exchange(ticker)
            if exchange == "UNKNOWN":
                exchange = config.get("stocks", "default_exchange", default="B3")

        collector = self.get_collector(exchange)
        return collector.get_quote(ticker)

    def get_history(
        self,
        ticker: str,
        exchange: Optional[str] = None,
        period: str = "1mo",
        interval: str = "1d",
    ) -> StockHistory:
        """Obtém histórico de preços."""
        if exchange is None:
            exchange = detect_exchange(ticker)
            if exchange == "UNKNOWN":
                exchange = config.get("stocks", "default_exchange", default="B3")

        collector = self.get_collector(exchange)
        return collector.get_history(ticker, period=period, interval=interval)

    def get_fundamentals(
        self, ticker: str, exchange: Optional[str] = None
    ) -> Optional[StockFundamentals]:
        """Obtém dados fundamentalistas."""
        if exchange is None:
            exchange = detect_exchange(ticker)
            if exchange == "UNKNOWN":
                exchange = config.get("stocks", "default_exchange", default="B3")

        collector = self.get_collector(exchange)
        fund_data = collector.get_fundamentals(ticker)

        # Tenta dados extras do Fundamentus para B3
        if exchange == "B3" and fund_data:
            try:
                extra = self.fundamentus.get_indicators(ticker)
                if extra.get("dy") and fund_data.dividend_yield is None:
                    fund_data.dividend_yield = extra["dy"]
            except StockCollectorError:
                pass  # Fallback silencioso

        return fund_data

    def analyze(self, ticker: str, exchange: Optional[str] = None) -> Dict[str, Any]:
        """
        Análise completa de uma ação usando IA local.

        Args:
            ticker: Ticker da ação (ex: PETR4, AAPL).
            exchange: Bolsa (B3, NYSE). Auto-detectado se omitido.

        Returns:
            Dict com cotação, fundamentos e análise IA.
        """
        # 1. Obtém dados
        quote = self.get_quote(ticker, exchange)
        fund = self.get_fundamentals(ticker, exchange or detect_exchange(ticker))

        # 2. Prepara prompt para IA
        prompt = format_stock_analysis_prompt(quote.to_dict(), fund.to_dict() if fund else None)

        # 3. Gera análise com IA local
        if self.check_llm_available():
            analysis = self.get_llm_analysis(
                prompt,
                system_prompt=FINANCIAL_ANALYSIS_SYSTEM_PROMPT,
            )
        else:
            analysis = "IA local não disponível. Use 'ollama serve' para ativar."

        # 4. Salva no histórico
        history = StockQueryHistory(
            ticker=quote.ticker,
            exchange=quote.exchange,
            query_type="analysis",
            result_summary=analysis[:500] if analysis else "",
        )
        self.save_to_history(history)

        return {
            "quote": quote,
            "fundamentals": fund,
            "analysis": analysis,
            "timestamp": datetime.now(),
        }

    def compare(self, tickers: List[str]) -> Dict[str, Any]:
        """
        Compara múltiplas ações usando IA.

        Args:
            tickers: Lista de tickers para comparar.

        Returns:
            Dict com cotações e análise comparativa.
        """
        if len(tickers) < 2:
            raise ValueError("Compare pelo menos 2 ações.")

        quotes = []
        fund_list = []

        for ticker in tickers:
            exchange = detect_exchange(ticker)
            try:
                q = self.get_quote(ticker, exchange)
                quotes.append(q)
                f = self.get_fundamentals(ticker, exchange)
                fund_list.append(f)
            except StockCollectorError as e:
                raise AgentError(f"Erro ao obter dados de {ticker}: {e}")

        # Prepara prompt de comparação
        ticker_data = []
        for q, f in zip(quotes, fund_list):
            info = f"📈 {q.ticker} ({q.exchange}): R$ {q.price:.2f} ({q.change_percent:+.2f}%)"
            if f:
                info += f" | P/L: {f.pe_ratio or 'N/A'} | DY: {f.dividend_yield or 'N/A'}"
            ticker_data.append(info)

        prompt = FINANCIAL_COMPARISON_PROMPT.format(
            ações="\n".join(ticker_data)
        )

        if self.check_llm_available():
            analysis = self.get_llm_analysis(
                prompt,
                system_prompt=FINANCIAL_ANALYSIS_SYSTEM_PROMPT,
            )
        else:
            analysis = "IA local não disponível."

        return {
            "quotes": quotes,
            "fundamentals": fund_list,
            "analysis": analysis,
            "timestamp": datetime.now(),
        }
