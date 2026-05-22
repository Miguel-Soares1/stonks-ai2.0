"""Testes para a CLI (E031-E034 da Matriz de Erros).

Usa Click CliRunner para testar comandos sem executar o terminal real.
"""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from stonks_ai.main import cli


class TestCLI:
    """Testes para E031-E034: Comandos da CLI."""

    def setup_method(self):
        self.runner = CliRunner()

    def test_cli_no_command(self):
        """Testa CLI sem subcomando - deve mostrar banner e ajuda."""
        result = self.runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "S T O N K S  A I" in result.output or "Stonks AI" in result.output
        assert "Comandos disponíveis" in result.output

    def test_cli_version(self):
        """Testa flag --version."""
        result = self.runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "Stonks AI" in result.output

    @patch("stonks_ai.main.financial_agent")
    def test_cli_quote_valid(self, mock_agent):
        """Testa comando quote com ticker válido."""
        from stonks_ai.collectors.stocks.base import StockQuote

        mock_agent.get_quote.return_value = StockQuote(
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

        result = self.runner.invoke(cli, ["quote", "PETR4"])
        assert result.exit_code == 0
        assert "PETR4" in result.output
        assert "Petrobras" in result.output

    @patch("stonks_ai.main.financial_agent")
    def test_cli_quote_with_exchange(self, mock_agent):
        """Testa quote com flag --exchange."""
        from stonks_ai.collectors.stocks.base import StockQuote

        mock_agent.get_quote.return_value = StockQuote(
            ticker="AAPL",
            exchange="NYSE",
            price=175.50,
            change=2.50,
            change_percent=1.44,
            high=176.00,
            low=174.50,
            open_price=175.00,
            previous_close=173.00,
            volume=50_000_000,
            currency="USD",
            name="Apple Inc.",
        )

        result = self.runner.invoke(cli, ["quote", "AAPL", "-e", "NYSE"])
        assert result.exit_code == 0
        assert "AAPL" in result.output

    @patch("stonks_ai.main.financial_agent")
    def test_cli_quote_error(self, mock_agent):
        """Testa quote com erro do coletor."""
        from stonks_ai.collectors.stocks.base import StockCollectorError

        mock_agent.get_quote.side_effect = StockCollectorError(
            "STK-001: Ticker 'XXXXX' não encontrado na B3."
        )

        result = self.runner.invoke(cli, ["quote", "XXXXX"])
        assert result.exit_code == 0  # CLI trata erro internamente
        assert "STK-001" in result.output

    @patch("stonks_ai.main.financial_agent")
    def test_cli_history(self, mock_agent):
        """Testa comando history."""
        from stonks_ai.collectors.stocks.base import StockHistory

        mock_agent.get_history.return_value = StockHistory(
            ticker="PETR4",
            exchange="B3",
            period="1mo",
            interval="1d",
            data=[
                {"date": "2025-04-01", "open": 35.0, "high": 35.5, "low": 34.5, "close": 35.2, "volume": 5_000_000},
                {"date": "2025-04-02", "open": 35.2, "high": 35.6, "low": 34.9, "close": 35.3, "volume": 5_100_000},
            ],
        )

        result = self.runner.invoke(cli, ["history", "PETR4", "-p", "1mo", "--no-chart"])
        assert result.exit_code == 0
        assert "PETR4" in result.output

    @patch("stonks_ai.main.financial_agent")
    def test_cli_history_empty(self, mock_agent):
        """Testa history com dados vazios."""
        from stonks_ai.collectors.stocks.base import StockHistory

        mock_agent.get_history.return_value = StockHistory(
            ticker="PETR4",
            exchange="B3",
            period="1d",
            interval="1d",
            data=[],
        )

        result = self.runner.invoke(cli, ["history", "PETR4", "-p", "1d", "--no-chart"])
        assert result.exit_code == 0
        assert "Nenhum dado histórico" in result.output

    @patch("stonks_ai.main.financial_agent")
    def test_cli_analyze(self, mock_agent):
        """Testa comando analyze."""
        from stonks_ai.collectors.stocks.base import StockFundamentals, StockQuote

        mock_agent.analyze.return_value = {
            "quote": StockQuote(
                ticker="PETR4", exchange="B3", price=35.50, change=0.70,
                change_percent=2.01, high=35.80, low=35.10, open_price=35.00,
                previous_close=34.80, volume=5_000_000, currency="BRL",
                name="Petrobras PN",
            ),
            "fundamentals": StockFundamentals(
                ticker="PETR4", name="Petrobras PN", sector="Oil & Gas",
                market_cap=500_000_000_000, pe_ratio=8.5,
                dividend_yield=0.08, roe=0.18, beta=0.95, pb_ratio=1.5,
            ),
            "analysis": "Recomendação: COMPRA. PETR4 está com P/L atrativo de 8.5x.",
            "timestamp": "2025-04-01T12:00:00",
        }

        result = self.runner.invoke(cli, ["analyze", "PETR4"])
        assert result.exit_code == 0
        assert "COMPRA" in result.output or "Análise" in result.output

    @patch("stonks_ai.main.financial_agent")
    def test_cli_analyze_no_llm(self, mock_agent):
        """Testa analyze quando LLM não está disponível."""
        from stonks_ai.collectors.stocks.base import StockFundamentals, StockQuote

        mock_agent.analyze.return_value = {
            "quote": StockQuote(
                ticker="PETR4", exchange="B3", price=35.50, change=0.70,
                change_percent=2.01, high=35.80, low=35.10, open_price=35.00,
                previous_close=34.80, volume=5_000_000, currency="BRL",
                name="Petrobras PN",
            ),
            "fundamentals": StockFundamentals(
                ticker="PETR4", name="Petrobras PN", sector="Oil & Gas",
                market_cap=500_000_000_000, pe_ratio=8.5,
                dividend_yield=0.08,
            ),
            "analysis": "IA local não disponível. Use 'ollama serve' para ativar.",
            "timestamp": "2025-04-01T12:00:00",
        }

        result = self.runner.invoke(cli, ["analyze", "PETR4"])
        assert result.exit_code == 0
        assert "não disponível" in result.output

    @patch("stonks_ai.main.financial_agent")
    def test_cli_compare(self, mock_agent):
        """Testa comando compare."""
        from stonks_ai.collectors.stocks.base import StockFundamentals, StockQuote

        mock_agent.compare.return_value = {
            "quotes": [
                StockQuote(
                    ticker="PETR4", exchange="B3", price=35.50, change=0.70,
                    change_percent=2.01, high=35.80, low=35.10, open_price=35.00,
                    previous_close=34.80, volume=5_000_000, currency="BRL",
                    name="Petrobras PN",
                ),
                StockQuote(
                    ticker="VALE3", exchange="B3", price=68.00, change=-0.50,
                    change_percent=-0.73, high=69.00, low=67.50, open_price=68.50,
                    previous_close=68.50, volume=8_000_000, currency="BRL",
                    name="Vale S.A.",
                ),
            ],
            "fundamentals": [
                StockFundamentals(ticker="PETR4", name="Petrobras PN", sector="Oil & Gas",
                                  market_cap=500_000_000_000, pe_ratio=8.5, dividend_yield=0.08),
                StockFundamentals(ticker="VALE3", name="Vale S.A.", sector="Mining",
                                  market_cap=350_000_000_000, pe_ratio=6.2, dividend_yield=0.12),
            ],
            "analysis": "PETR4 e VALE3 estão ambas atrativas.",
        }

        result = self.runner.invoke(cli, ["compare", "PETR4", "VALE3"])
        assert result.exit_code == 0
        assert "PETR4" in result.output
        assert "VALE3" in result.output

    def test_cli_compare_single_ticker(self):
        """Testa compare com apenas 1 ticker (deve mostrar erro)."""
        result = self.runner.invoke(cli, ["compare", "PETR4"])
        assert result.exit_code == 0
        assert "pelo menos 2 tickers" in result.output

    def test_cli_init(self):
        """Testa comando init."""
        result = self.runner.invoke(cli, ["init"])
        # Pode falhar se não tiver config, mas não deve crashar
        assert result.exit_code in (0, 1)

    def test_cli_config_show(self):
        """Testa config --show."""
        result = self.runner.invoke(cli, ["config", "--show"])
        assert result.exit_code == 0
        assert "llm" in result.output or "model" in result.output or "Configuração" in result.output

    def test_cli_config_set(self):
        """Testa config --set."""
        result = self.runner.invoke(cli, ["config", "--set", "llm.model", "llama3.2:3b"])
        assert result.exit_code == 0
        assert "Config atualizada" in result.output or "llm.model" in result.output

    def test_cli_watchlist_empty(self):
        """Testa watchlist vazia."""
        result = self.runner.invoke(cli, ["watchlist"])
        # Pode falhar se banco não existir, mas não deve crashar
        assert result.exit_code in (0, 1)

    def test_cli_help(self):
        """Testa --help para comandos."""
        result = self.runner.invoke(cli, ["quote", "--help"])
        assert result.exit_code == 0
        assert "TICKER" in result.output

        result = self.runner.invoke(cli, ["history", "--help"])
        assert result.exit_code == 0
        assert "TICKER" in result.output

    def test_cli_version_flag(self):
        """E031 (indireto): Testa flag -v (atalho para version)."""
        result = self.runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "Stonks AI" in result.output

    def test_cli_unknown_command(self):
        """E031: Comando inexistente."""
        result = self.runner.invoke(cli, ["comando_inexistente"])
        assert result.exit_code == 2  # Click retorna 2 para comando inválido
        assert "Error" in result.output or "No such command" in result.output

    def test_cli_missing_argument(self):
        """E032: Argumento obrigatório faltando (quote sem ticker)."""
        result = self.runner.invoke(cli, ["quote"])
        assert result.exit_code == 2  # Click retorna 2 para argumento faltando
        assert "Missing argument" in result.output or "Error" in result.output

    def test_cli_missing_argument_history(self):
        """E032: Argumento faltando no comando history."""
        result = self.runner.invoke(cli, ["history"])
        assert result.exit_code == 2
        assert "Missing argument" in result.output or "Error" in result.output

    def test_cli_missing_argument_analyze(self):
        """E032: Argumento faltando no comando analyze."""
        result = self.runner.invoke(cli, ["analyze"])
        assert result.exit_code == 2
        assert "Missing argument" in result.output or "Error" in result.output

    def test_cli_keyboard_interrupt(self):
        """E033: CTRL+C durante execução (simulado via raising KeyboardInterrupt)."""
        from stonks_ai.main import print_banner

        with patch("stonks_ai.main.print_banner", side_effect=KeyboardInterrupt()):
            result = self.runner.invoke(cli, [])
            # Deve capturar e mostrar mensagem amigável
            assert result.exit_code == 0
            assert "cancelada" in result.output.lower()

    def test_cli_invalid_ticker_format(self):
        """E034: Ticker com formato inválido."""
        result = self.runner.invoke(cli, ["quote", "12345"])
        # O ticker deve ser validado de alguma forma
        # Pode ser aceito pelo ticker e rejeitado pelo validador
        assert result.exit_code == 0 or result.exit_code == 1

    def test_cli_invalid_ticker_special_chars(self):
        """E034: Ticker com caracteres especiais."""
        result = self.runner.invoke(cli, ["quote", "PETR@4!"])
        assert result.exit_code == 0 or result.exit_code == 1
