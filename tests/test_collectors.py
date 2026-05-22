"""Testes para coletores de dados financeiros (E001-E010 da Matriz de Erros)."""

from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import MagicMock, PropertyMock, patch

import httpx
import pandas as pd
import pytest

from stonks_ai.collectors.stocks.b3 import B3Collector
from stonks_ai.collectors.stocks.base import (
    StockCollectorError,
    StockFundamentals,
    StockHistory,
    StockQuote,
)
from stonks_ai.collectors.stocks.fundamental_data import FundamentalDataCollector
from stonks_ai.collectors.stocks.nyse import NYSECollector


# ====== Mocks ======

def make_mock_info(overrides: Dict[str, Any] = None) -> Dict[str, Any]:
    """Cria dados mockados de info do yfinance."""
    data = {
        "regularMarketPrice": 35.50,
        "currentPrice": 35.50,
        "regularMarketPreviousClose": 34.80,
        "previousClose": 34.80,
        "regularMarketDayHigh": 35.80,
        "dayHigh": 35.80,
        "regularMarketDayLow": 35.10,
        "dayLow": 35.10,
        "regularMarketOpen": 35.00,
        "open": 35.00,
        "regularMarketVolume": 5_000_000,
        "volume": 5_000_000,
        "longName": "Petrobras PN",
        "shortName": "PETR4",
        "marketCap": 500_000_000_000,
        "sector": "Oil & Gas",
        "trailingPE": 8.5,
        "forwardPE": 7.2,
        "dividendYield": 0.08,
        "trailingEps": 4.18,
        "beta": 0.95,
        "priceToBook": 1.5,
        "returnOnEquity": 0.18,
        "profitMargins": 0.12,
        "debtToEquity": 0.45,
        "totalRevenue": 120_000_000_000,
        "netIncomeToCommon": 30_000_000_000,
        "freeCashflow": 25_000_000_000,
        "industry": "Oil & Gas Integrated",
    }
    if overrides:
        data.update(overrides)
    return data


def make_mock_ticker(info_data: Dict[str, Any] = None, history_empty: bool = False):
    """Cria um mock de yf.Ticker."""
    mock_ticker = MagicMock()
    mock_ticker.info = info_data or make_mock_info()

    if history_empty:
        mock_ticker.history.return_value = pd.DataFrame()
    else:
        dates = pd.date_range(start="2025-04-01", periods=30, freq="D")
        mock_hist = pd.DataFrame({
            "Open": [35.0 + i * 0.1 for i in range(30)],
            "High": [35.5 + i * 0.1 for i in range(30)],
            "Low": [34.5 + i * 0.1 for i in range(30)],
            "Close": [35.0 + i * 0.1 for i in range(30)],
            "Volume": [5_000_000 + i * 1000 for i in range(30)],
        }, index=dates)
        mock_ticker.history.return_value = mock_hist

    return mock_ticker


# ====== Testes B3Collector ======

class TestB3Collector:
    """Testes para E001-E006: B3 Stock Collector."""

    def setup_method(self):
        self.collector = B3Collector()

    @patch("yfinance.Ticker")
    def test_b3_get_quote_valid(self, mock_ticker_cls):
        """Testa cotação válida na B3."""
        mock_ticker = make_mock_ticker()
        mock_ticker_cls.return_value = mock_ticker

        quote = self.collector.get_quote("PETR4")

        assert quote.ticker == "PETR4"
        assert quote.exchange == "B3"
        assert quote.price == 35.50
        assert quote.change == 0.70
        assert quote.currency == "BRL"

    @patch("yfinance.Ticker")
    def test_b3_invalid_ticker(self, mock_ticker_cls):
        """E001: Ticker B3 inválido."""
        mock_ticker = make_mock_ticker(history_empty=True)
        mock_ticker.info = {}
        mock_ticker_cls.return_value = mock_ticker

        with pytest.raises(StockCollectorError) as exc:
            self.collector.get_quote("XXXXX")
        assert "STK-001" in str(exc.value)

    @patch("yfinance.Ticker")
    def test_b3_ticker_suffix(self, mock_ticker_cls):
        """E002: Ticker sem sufixo .SA - deve adicionar automaticamente."""
        mock_ticker = make_mock_ticker()
        mock_ticker_cls.return_value = mock_ticker

        # Ticker PETR4 (sem .SA) deve ser convertido internamente
        quote = self.collector.get_quote("petr4")
        assert quote.ticker == "PETR4"  # Deve normalizar para upper

    @patch("yfinance.Ticker")
    def test_b3_network_error(self, mock_ticker_cls):
        """E003: Sem conexão com Yahoo Finance."""
        mock_ticker_cls.side_effect = ConnectionError("No internet")

        with pytest.raises(StockCollectorError) as exc:
            self.collector.get_quote("PETR4")
        assert "STK-003" in str(exc.value)

    @patch("yfinance.download")
    def test_b3_empty_history(self, mock_download):
        """E004: Dados históricos vazios."""
        mock_download.return_value = pd.DataFrame()

        with pytest.raises(StockCollectorError) as exc:
            self.collector.get_history("PETR4", period="1mo")
        assert "STK-004" in str(exc.value)

    @patch("yfinance.Ticker")
    def test_b3_parse_error(self, mock_ticker_cls):
        """Testa erro de parsing quando dados são inválidos."""
        mock_ticker = make_mock_ticker({"regularMarketPrice": None, "currentPrice": None})
        mock_ticker_cls.return_value = mock_ticker

        # Deve retornar 0.0 para price, não lançar exceção
        quote = self.collector.get_quote("PETR4")
        assert quote.price == 0.0

    @patch("yfinance.Ticker")
    def test_b3_us_ticker_detection(self, mock_ticker_cls):
        """E006: Ticker americano na B3 - não deve lançar erro (validação é do agente)."""
        mock_ticker = make_mock_ticker()
        mock_ticker_cls.return_value = mock_ticker

        # O B3Collector aceita qualquer ticker e adiciona .SA
        quote = self.collector.get_quote("AAPL")
        assert quote.ticker == "AAPL"

    @patch("yfinance.Ticker")
    def test_b3_get_fundamentals(self, mock_ticker_cls):
        """Testa obtenção de dados fundamentalistas B3."""
        mock_ticker = make_mock_ticker()
        mock_ticker_cls.return_value = mock_ticker

        fund = self.collector.get_fundamentals("PETR4")

        assert fund is not None
        assert fund.ticker == "PETR4"
        assert fund.pe_ratio == 8.5
        assert fund.market_cap == 500_000_000_000
        assert fund.sector == "Oil & Gas"

    @patch("yfinance.Ticker")
    def test_b3_get_fundamentals_none(self, mock_ticker_cls):
        """Testa fundamental data None quando marketCap não disponível."""
        mock_ticker = make_mock_ticker({"marketCap": None})
        mock_ticker_cls.return_value = mock_ticker

        fund = self.collector.get_fundamentals("PETR4")
        assert fund is None

    @patch("yfinance.download")
    def test_b3_get_history(self, mock_download):
        """Testa obtenção de histórico B3."""
        dates = pd.date_range(start="2025-04-01", periods=5, freq="D")
        mock_download.return_value = pd.DataFrame({
            "Open": [35.0, 35.2, 35.1, 35.5, 35.3],
            "High": [35.5, 35.6, 35.4, 35.8, 35.7],
            "Low": [34.8, 34.9, 34.7, 35.0, 34.9],
            "Close": [35.2, 35.3, 35.0, 35.6, 35.4],
            "Volume": [5_000_000, 5_100_000, 4_900_000, 5_200_000, 5_050_000],
        }, index=dates)

        hist = self.collector.get_history("PETR4", period="5d")

        assert hist.ticker == "PETR4"
        assert hist.exchange == "B3"
        assert len(hist.data) == 5
        assert "date" in hist.data[0]
        assert "close" in hist.data[0]
        assert "volume" in hist.data[0]

    @patch("yfinance.download")
    def test_b3_history_download_error(self, mock_download):
        """Testa erro de rede ao baixar histórico."""
        mock_download.side_effect = Exception("API error")

        with pytest.raises(StockCollectorError) as exc:
            self.collector.get_history("PETR4", period="1mo")
        assert "STK-003" in str(exc.value)


# ====== Testes NYSECollector ======

class TestNYSEcollector:
    """Testes para E007-E010: NYSE/Nasdaq Stock Collector."""

    def setup_method(self):
        self.collector = NYSECollector()

    @patch("yfinance.Ticker")
    def test_nyse_get_quote_valid(self, mock_ticker_cls):
        """Testa cotação válida na NYSE."""
        info = make_mock_info({
            "longName": "Apple Inc.",
            "shortName": "AAPL",
            "regularMarketPrice": 175.50,
            "currency": "USD",
        })
        mock_ticker = make_mock_ticker(info)
        mock_ticker_cls.return_value = mock_ticker

        quote = self.collector.get_quote("AAPL")

        assert quote.ticker == "AAPL"
        assert quote.exchange == "NYSE"
        assert quote.price == 175.50
        assert quote.currency == "USD"

    @patch("yfinance.Ticker")
    def test_nyse_invalid_ticker(self, mock_ticker_cls):
        """E007: Ticker NYSE inválido."""
        mock_ticker = make_mock_ticker(history_empty=True)
        mock_ticker.info = {}
        mock_ticker_cls.return_value = mock_ticker

        with pytest.raises(StockCollectorError) as exc:
            self.collector.get_quote("ZZZZZ")
        assert "STK-007" in str(exc.value)

    def test_nyse_br_ticker_detection(self):
        """E008: Ticker brasileiro detectado na NYSE."""
        with pytest.raises(StockCollectorError) as exc:
            self.collector.get_quote("PETR4")
        assert "STK-008" in str(exc.value)

    def test_nyse_br_ticker_with_suffix(self):
        """E008: Ticker brasileiro com .SA detectado na NYSE."""
        with pytest.raises(StockCollectorError) as exc:
            self.collector.get_quote("VALE3.SA")
        assert "STK-008" in str(exc.value)

    @patch("yfinance.Ticker")
    def test_nyse_no_fundamentals(self, mock_ticker_cls):
        """E009: Dados fundamentalistas indisponíveis na NYSE."""
        mock_ticker = make_mock_ticker({"marketCap": None})
        mock_ticker_cls.return_value = mock_ticker

        fund = self.collector.get_fundamentals("AAPL")
        assert fund is None

    @patch("yfinance.Ticker")
    def test_nyse_timeout(self, mock_ticker_cls):
        """E010: Timeout na conexão Yahoo Finance NYSE."""
        mock_ticker_cls.side_effect = TimeoutError("Connection timed out")

        with pytest.raises(StockCollectorError) as exc:
            self.collector.get_quote("AAPL")
        assert "STK-010" in str(exc.value)

    @patch("yfinance.Ticker")
    def test_nyse_get_fundamentals(self, mock_ticker_cls):
        """Testa obtenção de dados fundamentalistas NYSE."""
        info = make_mock_info({
            "longName": "Apple Inc.",
            "marketCap": 2_800_000_000_000,
            "sector": "Technology",
            "currency": "USD",
        })
        mock_ticker = make_mock_ticker(info)
        mock_ticker_cls.return_value = mock_ticker

        fund = self.collector.get_fundamentals("AAPL")

        assert fund is not None
        assert fund.ticker == "AAPL"
        assert fund.market_cap == 2_800_000_000_000
        assert fund.sector == "Technology"
        assert fund.currency == "USD"

    @patch("yfinance.download")
    def test_nyse_get_history(self, mock_download):
        """Testa obtenção de histórico NYSE."""
        dates = pd.date_range(start="2025-04-01", periods=10, freq="D")
        mock_download.return_value = pd.DataFrame({
            "Open": [175.0, 176.0, 175.5, 177.0, 176.5, 178.0, 177.5, 179.0, 178.5, 180.0],
            "High": [176.0, 177.0, 176.5, 178.0, 177.5, 179.0, 178.5, 180.0, 179.5, 181.0],
            "Low": [174.5, 175.5, 174.8, 176.0, 175.5, 177.0, 176.5, 178.0, 177.5, 179.0],
            "Close": [175.5, 176.5, 175.8, 177.2, 176.8, 178.3, 177.8, 179.2, 178.8, 180.3],
            "Volume": [50_000_000, 52_000_000, 48_000_000, 55_000_000, 51_000_000,
                       60_000_000, 53_000_000, 58_000_000, 54_000_000, 62_000_000],
        }, index=dates)

        hist = self.collector.get_history("AAPL", period="10d")

        assert hist.ticker == "AAPL"
        assert hist.exchange == "NYSE"
        assert len(hist.data) == 10

    @patch("yfinance.download")
    def test_nyse_empty_history(self, mock_download):
        """E004/010: Histórico vazio na NYSE."""
        mock_download.return_value = pd.DataFrame()

        with pytest.raises(StockCollectorError) as exc:
            self.collector.get_history("AAPL", period="1d")
        assert "STK-004" in str(exc.value)

    def test_is_brazilian_ticker(self):
        """Testa detecção de tickers brasileiros."""
        assert NYSECollector._is_brazilian_ticker("PETR4")
        assert NYSECollector._is_brazilian_ticker("VALE3")
        assert NYSECollector._is_brazilian_ticker("PETR4.SA")
        assert not NYSECollector._is_brazilian_ticker("AAPL")
        assert not NYSECollector._is_brazilian_ticker("MSFT")
        assert not NYSECollector._is_brazilian_ticker("GOOGL")


# ====== Testes FundamentalDataCollector ======

class TestFundamentalDataCollector:
    """Testes para o coletor de dados fundamentalistas (Fundamentus)."""

    def setup_method(self):
        self.collector = FundamentalDataCollector(timeout=10)

    def teardown_method(self):
        self.collector.close()

    @patch("httpx.Client.get")
    def test_get_indicators_success(self, mock_get):
        """Testa obtenção de indicadores do Fundamentus."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <body>
                <table>
                    <tr><td>P/L</td><td>8,50</td></tr>
                    <tr><td>P/VP</td><td>1,50</td></tr>
                    <tr><td>Div.Yield</td><td>8,00%</td></tr>
                    <tr><td>ROE</td><td>18,00%</td></tr>
                    <tr><td>Marg. Líquida</td><td>12,00%</td></tr>
                    <tr><td>Dív. Líquida / Patrimônio</td><td>0,45</td></tr>
                </table>
            </body>
        </html>
        """
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        indicators = self.collector.get_indicators("PETR4")

        assert indicators["ticker"] == "PETR4"
        assert indicators["pl"] == 8.50
        assert indicators["pvp"] == 1.50
        assert indicators["dy"] == 0.08
        assert indicators["roe"] == 18.00
        assert indicators["margem_liquida"] == 12.00
        assert indicators["div_liq_pat"] == 0.45

    @patch("httpx.Client.get")
    def test_get_indicators_404(self, mock_get):
        """E001: Ticker não encontrado no Fundamentus."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=mock_response
        )
        mock_get.return_value = mock_response

        with pytest.raises(StockCollectorError) as exc:
            self.collector.get_indicators("XXXXX")
        assert "STK-001" in str(exc.value)

    @patch("httpx.Client.get")
    def test_get_indicators_timeout(self, mock_get):
        """E010: Timeout no Fundamentus."""
        mock_get.side_effect = httpx.TimeoutException("Timeout")

        with pytest.raises(StockCollectorError) as exc:
            self.collector.get_indicators("PETR4")
        assert "STK-010" in str(exc.value)

    def test_parse_br_number(self):
        """Testa parsing de números no formato brasileiro."""
        assert FundamentalDataCollector._parse_br_number("1.234,56") == 1234.56
        assert FundamentalDataCollector._parse_br_number("1500,00") == 1500.00
        assert FundamentalDataCollector._parse_br_number("1000") == 1000.0
        assert FundamentalDataCollector._parse_br_number("8,50") == 8.50
        assert FundamentalDataCollector._parse_br_number("-") is None
        assert FundamentalDataCollector._parse_br_number("N/A") is None
        assert FundamentalDataCollector._parse_br_number("") is None
        assert FundamentalDataCollector._parse_br_number("R$ 1.234,56") == 1234.56
        assert FundamentalDataCollector._parse_br_number("18,00%") == 18.00


# ====== Testes das Dataclasses Base ======

class TestStockDataclasses:
    """Testes para as dataclasses StockQuote, StockHistory, StockFundamentals."""

    def test_stock_quote_to_dict(self):
        """Testa conversão de StockQuote para dict."""
        quote = StockQuote(
            ticker="PETR4",
            exchange="B3",
            price=35.50,
            change=0.70,
            change_percent=2.01,
            high=35.80,
            low=35.10,
            open_price=35.00,
            previous_close=34.80,
            volume=5_000_000,
            currency="BRL",
            name="Petrobras PN",
        )
        data = quote.to_dict()
        assert data["ticker"] == "PETR4"
        assert data["price"] == 35.50
        assert data["currency"] == "BRL"
        assert data["exchange"] == "B3"

    def test_stock_history_creation(self):
        """Testa criação de StockHistory."""
        data = [
            {"date": "2025-04-01", "open": 35.0, "high": 35.5, "low": 34.5, "close": 35.2, "volume": 5_000_000},
            {"date": "2025-04-02", "open": 35.2, "high": 35.6, "low": 34.9, "close": 35.3, "volume": 5_100_000},
        ]
        hist = StockHistory(
            ticker="PETR4",
            exchange="B3",
            period="1mo",
            interval="1d",
            data=data,
        )
        assert len(hist.data) == 2
        assert hist.period == "1mo"

    def test_stock_fundamentals_defaults(self):
        """Testa criação de StockFundamentals com valores padrão."""
        fund = StockFundamentals(
            ticker="PETR4",
            name="Petrobras PN",
            sector="Oil & Gas",
            market_cap=500_000_000_000,
        )
        assert fund.pe_ratio is None
        assert fund.dividend_yield is None
        assert fund.currency == "BRL"

    def test_stock_collector_error(self):
        """Testa criação de StockCollectorError."""
        error = StockCollectorError("STK-001: Ticker inválido")
        assert str(error) == "STK-001: Ticker inválido"


class TestRateLimit:
    """E005: Testes para limite de requisições (rate limit)."""

    @patch("yfinance.Ticker")
    def test_b3_rate_limit_on_get_quote(self, mock_ticker_cls):
        """E005: Rate limit ao obter cotação na B3."""
        mock_ticker = MagicMock()
        # Usa PropertyMock para que o acesso ao atributo .info dispare a exceção
        mock_info = PropertyMock(side_effect=Exception("Rate limit: HTTP error 429: Too Many Requests"))
        type(mock_ticker).info = mock_info
        mock_ticker_cls.return_value = mock_ticker

        collector = B3Collector()
        with pytest.raises(StockCollectorError) as exc:
            collector.get_quote("PETR4")

        assert "STK-005" in str(exc.value)
        assert "Limite de requisições" in str(exc.value)

    @patch("yfinance.Ticker")
    def test_b3_rate_limit_rate_limit_keyword(self, mock_ticker_cls):
        """E005: Rate limit detectado pela palavra 'rate limit'."""
        mock_ticker = MagicMock()
        # Usa PropertyMock para que o acesso ao atributo .info dispare a exceção
        mock_info = PropertyMock(side_effect=Exception("Rate limit exceeded. Please retry."))
        type(mock_ticker).info = mock_info
        mock_ticker_cls.return_value = mock_ticker

        collector = B3Collector()
        with pytest.raises(StockCollectorError) as exc:
            collector.get_quote("VALE3")

        assert "STK-005" in str(exc.value)

    @patch("yfinance.download")
    def test_b3_rate_limit_on_history(self, mock_download):
        """E005: Rate limit ao baixar histórico na B3."""
        mock_download.side_effect = Exception("rate limit exceeded")

        collector = B3Collector()
        with pytest.raises(StockCollectorError) as exc:
            collector.get_history("PETR4", period="1mo")

        assert "STK-005" in str(exc.value)

    @patch("yfinance.Ticker")
    def test_nyse_rate_limit(self, mock_ticker_cls):
        """E005: Rate limit na NYSE."""
        mock_ticker = MagicMock()
        # Usa PropertyMock para que o acesso ao atributo .info dispare a exceção
        mock_info = PropertyMock(side_effect=Exception("Rate limit: 429 Too Many Requests"))
        type(mock_ticker).info = mock_info
        mock_ticker_cls.return_value = mock_ticker

        collector = NYSECollector()
        with pytest.raises(StockCollectorError) as exc:
            collector.get_quote("AAPL")

        assert "STK-005" in str(exc.value)
