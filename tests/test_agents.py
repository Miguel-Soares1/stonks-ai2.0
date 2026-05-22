"""Testes de integração para agentes de IA e fluxos completos."""

from unittest.mock import MagicMock, patch

import pytest

from stonks_ai.agents.financial_agent import FinancialAgent
from stonks_ai.collectors.stocks.base import (
    StockCollectorError,
    StockFundamentals,
    StockHistory,
    StockQuote,
)


class TestFinancialAgent:
    """Testes para o FinancialAgent."""

    def setup_method(self):
        self.agent = FinancialAgent()
        # Mock do LLM para não depender de Ollama
        self.agent.llm.is_available = MagicMock(return_value=False)

    @patch("stonks_ai.agents.financial_agent.B3Collector")
    def test_get_quote_b3(self, mock_b3_cls):
        """Testa obtenção de cotação para B3."""
        mock_b3 = MagicMock()
        mock_b3.get_quote.return_value = StockQuote(
            ticker="PETR4", exchange="B3", price=35.50, change=0.70,
            change_percent=2.01, high=35.80, low=35.10, open_price=35.00,
            previous_close=34.80, volume=5_000_000, currency="BRL",
            name="Petrobras PN",
        )
        self.agent.b3 = mock_b3

        quote = self.agent.get_quote("PETR4", exchange="B3")
        assert quote.ticker == "PETR4"
        assert quote.exchange == "B3"
        assert quote.price == 35.50

    @patch("stonks_ai.agents.financial_agent.NYSECollector")
    def test_get_quote_nyse(self, mock_nyse_cls):
        """Testa obtenção de cotação para NYSE."""
        mock_nyse = MagicMock()
        mock_nyse.get_quote.return_value = StockQuote(
            ticker="AAPL", exchange="NYSE", price=175.50, change=2.50,
            change_percent=1.44, high=176.00, low=174.50, open_price=175.00,
            previous_close=173.00, volume=50_000_000, currency="USD",
            name="Apple Inc.",
        )
        self.agent.nyse = mock_nyse

        quote = self.agent.get_quote("AAPL", exchange="NYSE")
        assert quote.ticker == "AAPL"
        assert quote.exchange == "NYSE"
        assert quote.currency == "USD"

    def test_get_collector_invalid(self):
        """Testa exchange inválida."""
        with pytest.raises(ValueError, match="não suportada"):
            self.agent.get_collector("UNKNOWN")

    @patch("stonks_ai.agents.financial_agent.B3Collector")
    def test_get_quote_auto_detect_b3(self, mock_b3_cls):
        """Testa auto-detecção de B3 pelo ticker."""
        mock_b3 = MagicMock()
        mock_b3.get_quote.return_value = StockQuote(
            ticker="PETR4", exchange="B3", price=35.50, change=0.70,
            change_percent=2.01, high=35.80, low=35.10, open_price=35.00,
            previous_close=34.80, volume=5_000_000, currency="BRL",
            name="Petrobras PN",
        )
        self.agent.b3 = mock_b3

        # Sem especificar exchange - deve auto-detectar
        quote = self.agent.get_quote("PETR4")
        assert quote.ticker == "PETR4"
        assert quote.exchange == "B3"

    @patch("stonks_ai.agents.financial_agent.B3Collector")
    def test_get_history(self, mock_b3_cls):
        """Testa obtenção de histórico."""
        mock_b3 = MagicMock()
        mock_b3.get_history.return_value = StockHistory(
            ticker="PETR4", exchange="B3", period="1mo", interval="1d",
            data=[{"date": "2025-04-01", "close": 35.2, "volume": 5_000_000}],
        )
        self.agent.b3 = mock_b3

        hist = self.agent.get_history("PETR4", exchange="B3", period="1mo")
        assert hist.ticker == "PETR4"
        assert len(hist.data) == 1

    @patch("stonks_ai.agents.financial_agent.B3Collector")
    @patch("stonks_ai.agents.financial_agent.FundamentalDataCollector")
    def test_get_fundamentals(self, mock_fund_cls, mock_b3_cls):
        """Testa obtenção de fundamentos."""
        mock_b3 = MagicMock()
        mock_b3.get_fundamentals.return_value = StockFundamentals(
            ticker="PETR4", name="Petrobras PN", sector="Oil & Gas",
            market_cap=500_000_000_000, pe_ratio=8.5, dividend_yield=0.08,
        )
        self.agent.b3 = mock_b3

        mock_fund = MagicMock()
        mock_fund.get_indicators.return_value = {"dy": 8.5}
        self.agent.fundamentus = mock_fund

        fund = self.agent.get_fundamentals("PETR4", exchange="B3")
        assert fund is not None
        assert fund.ticker == "PETR4"
        assert fund.pe_ratio == 8.5

    @patch("stonks_ai.agents.financial_agent.B3Collector")
    @patch("stonks_ai.agents.financial_agent.FundamentalDataCollector")
    def test_analyze_without_llm(self, mock_fund_cls, mock_b3_cls):
        """Testa analyze sem LLM disponível."""
        mock_b3 = MagicMock()
        mock_b3.get_quote.return_value = StockQuote(
            ticker="PETR4", exchange="B3", price=35.50, change=0.70,
            change_percent=2.01, high=35.80, low=35.10, open_price=35.00,
            previous_close=34.80, volume=5_000_000, currency="BRL",
            name="Petrobras PN",
        )
        mock_b3.get_fundamentals.return_value = StockFundamentals(
            ticker="PETR4", name="Petrobras PN", sector="Oil & Gas",
            market_cap=500_000_000_000, pe_ratio=8.5,
        )
        self.agent.b3 = mock_b3
        self.agent.fundamentus = MagicMock()
        self.agent.fundamentus.get_indicators.return_value = {}

        result = self.agent.analyze("PETR4", exchange="B3")
        assert "quote" in result
        assert "fundamentals" in result
        assert "analysis" in result
        assert "não disponível" in result["analysis"].lower()

    @patch("stonks_ai.agents.financial_agent.B3Collector")
    @patch("stonks_ai.agents.financial_agent.FundamentalDataCollector")
    def test_analyze_with_llm(self, mock_fund_cls, mock_b3_cls):
        """Testa analyze com LLM disponível."""
        mock_b3 = MagicMock()
        mock_b3.get_quote.return_value = StockQuote(
            ticker="PETR4", exchange="B3", price=35.50, change=0.70,
            change_percent=2.01, high=35.80, low=35.10, open_price=35.00,
            previous_close=34.80, volume=5_000_000, currency="BRL",
            name="Petrobras PN",
        )
        mock_b3.get_fundamentals.return_value = StockFundamentals(
            ticker="PETR4", name="Petrobras PN", sector="Oil & Gas",
            market_cap=500_000_000_000, pe_ratio=8.5,
        )
        self.agent.b3 = mock_b3
        self.agent.fundamentus = MagicMock()
        self.agent.fundamentus.get_indicators.return_value = {}

        # Habilita LLM mockado
        self.agent.llm.is_available = MagicMock(return_value=True)
        self.agent.llm.generate = MagicMock(return_value="Recomendação: COMPRA. P/L atrativo.")

        result = self.agent.analyze("PETR4", exchange="B3")
        assert result["analysis"] == "Recomendação: COMPRA. P/L atrativo."

    @patch("stonks_ai.agents.financial_agent.B3Collector")
    @patch("stonks_ai.agents.financial_agent.NYSECollector")
    def test_compare(self, mock_nyse_cls, mock_b3_cls):
        """Testa comparação entre duas ações."""
        mock_b3 = MagicMock()
        mock_b3.get_quote.return_value = StockQuote(
            ticker="PETR4", exchange="B3", price=35.50, change=0.70,
            change_percent=2.01, high=35.80, low=35.10, open_price=35.00,
            previous_close=34.80, volume=5_000_000, currency="BRL",
            name="Petrobras PN",
        )
        mock_b3.get_fundamentals.return_value = StockFundamentals(
            ticker="PETR4", name="Petrobras PN", sector="Oil & Gas",
            market_cap=500_000_000_000, pe_ratio=8.5,
        )
        self.agent.b3 = mock_b3

        mock_nyse = MagicMock()
        mock_nyse.get_quote.return_value = StockQuote(
            ticker="XOM", exchange="NYSE", price=120.00, change=1.00,
            change_percent=0.84, high=121.00, low=119.00, open_price=119.50,
            previous_close=119.00, volume=15_000_000, currency="USD",
            name="Exxon Mobil Corp",
        )
        mock_nyse.get_fundamentals.return_value = StockFundamentals(
            ticker="XOM", name="Exxon Mobil Corp", sector="Oil & Gas",
            market_cap=500_000_000_000, pe_ratio=12.0,
        )
        self.agent.nyse = mock_nyse

        result = self.agent.compare(["PETR4", "XOM"])
        assert len(result["quotes"]) == 2
        assert len(result["fundamentals"]) == 2

    @patch("stonks_ai.agents.financial_agent.B3Collector")
    def test_compare_single_fails(self, mock_b3_cls):
        """Testa erro ao comparar menos de 2 ações."""
        with pytest.raises(ValueError, match="Compare pelo menos 2"):
            self.agent.compare(["PETR4"])

    @patch("stonks_ai.agents.financial_agent.B3Collector")
    def test_compare_with_error(self, mock_b3_cls):
        """Testa erro ao obter dados de um ticker na comparação."""
        mock_b3 = MagicMock()
        mock_b3.get_quote.side_effect = StockCollectorError(
            "STK-001: Ticker 'XXXXX' não encontrado"
        )
        self.agent.b3 = mock_b3

        from stonks_ai.agents.base_agent import AgentError
        with pytest.raises(AgentError):
            self.agent.compare(["PETR4", "XXXXX"])


