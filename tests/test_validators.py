"""Testes unitários para validadores."""

import pytest

from stonks_ai.utils.validators import (
    detect_exchange,
    validate_br_currency,
    validate_interval,
    validate_period,
    validate_ticker,
    validate_yes_no,
)


class TestValidators:
    """Testes para funções de validação."""

    def test_validate_ticker_b3_valid(self):
        """Testa tickers B3 válidos."""
        assert validate_ticker("PETR4", "B3")[0] is True
        assert validate_ticker("VALE3", "B3")[0] is True
        assert validate_ticker("ITUB4", "B3")[0] is True

    def test_validate_ticker_b3_invalid(self):
        """E001: Ticker B3 inválido."""
        assert validate_ticker("INVALIDO1", "B3")[0] is False
        assert validate_ticker("AB", "B3")[0] is False
        assert validate_ticker("12345", "B3")[0] is False

    def test_validate_ticker_nyse_valid(self):
        """Testa tickers NYSE válidos."""
        assert validate_ticker("AAPL", "NYSE")[0] is True
        assert validate_ticker("MSFT", "NYSE")[0] is True
        assert validate_ticker("GOOGL", "NYSE")[0] is True

    def test_validate_ticker_nyse_invalid(self):
        """E007: Ticker NYSE inválido."""
        assert validate_ticker("PETR4", "NYSE")[0] is False

    def test_validate_ticker_auto_detect(self):
        """Testa auto-detecção de bolsa."""
        assert detect_exchange("PETR4") == "B3"
        assert detect_exchange("VALE3.SA") == "B3"
        assert detect_exchange("AAPL") == "NYSE"
        assert detect_exchange("UNKNOW1") == "UNKNOWN"

    def test_validate_period_valid(self):
        """Testa períodos válidos."""
        assert validate_period("1d")[0] is True
        assert validate_period("1mo")[0] is True
        assert validate_period("1y")[0] is True
        assert validate_period("max")[0] is True

    def test_validate_period_invalid(self):
        """Testa período inválido."""
        assert validate_period("invalid")[0] is False

    def test_validate_interval_valid(self):
        """Testa intervalos válidos."""
        assert validate_interval("1d")[0] is True
        assert validate_interval("1wk")[0] is True

    def test_validate_interval_invalid(self):
        """Testa intervalo inválido."""
        assert validate_interval("10x")[0] is False

    def test_validate_br_currency(self):
        """Testa conversão de valores brasileiros."""
        assert validate_br_currency("R$ 1.234,56") == 1234.56
        assert validate_br_currency("1500,00") == 1500.00
        assert validate_br_currency("1000") == 1000.0
        assert validate_br_currency("") is None
        assert validate_br_currency("abc") is None

    def test_validate_yes_no(self):
        """Testa validação sim/não."""
        assert validate_yes_no("s") is True
        assert validate_yes_no("sim") is True
        assert validate_yes_no("n") is False
        assert validate_yes_no("não") is False
        assert validate_yes_no("talvez") is None
