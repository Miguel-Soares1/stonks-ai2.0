"""
Coletor de dados fundamentalistas da B3 via Fundamentus.

Fornece dados como P/L, P/VP, Dividend Yield, ROE, etc.
"""

import time
from typing import Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

from stonks_ai.collectors.stocks.base import StockCollectorError


class FundamentalDataCollector:
    """Coletor de dados fundamentalistas do mercado brasileiro."""

    BASE_URL = "https://www.fundamentus.com.br"
    # Rate limiting: mínimo de 1.5s entre requisições para evitar bloqueio
    REQUEST_INTERVAL = 1.5

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None
        self._last_request_time: float = 0.0

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.BASE_URL,
                timeout=self.timeout,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                },
            )
        return self._client

    def _rate_limit(self):
        """Garante intervalo mínimo entre requisições."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.REQUEST_INTERVAL:
            time.sleep(self.REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()

    def get_indicators(self, ticker: str) -> Dict[str, Optional[float]]:
        """Obtém indicadores fundamentalistas de um ticker da B3."""
        ticker = ticker.strip().upper().replace(".SA", "")

        self._rate_limit()

        try:
            response = self.client.get(f"/detalhes.php?papel={ticker}")
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise StockCollectorError(
                    f"STK-001: Ticker '{ticker}' não encontrado no Fundamentus."
                )
            raise StockCollectorError(
                f"STK-003: Erro ao acessar Fundamentus: {e}"
            )
        except httpx.TimeoutException:
            raise StockCollectorError(
                "STK-010: Timeout ao acessar Fundamentus."
            )

        soup = BeautifulSoup(response.text, "html.parser")
        indicators = self._parse_indicators(soup, ticker)
        return indicators

    def _parse_indicators(self, soup: BeautifulSoup, ticker: str) -> Dict[str, Optional[float]]:
        """Parsea os indicadores fundamentalistas da página HTML."""
        indicators: Dict[str, Optional[float]] = {
            "ticker": ticker,
            "pl": None,        # P/L
            "pvp": None,       # P/VP
            "dy": None,        # Dividend Yield
            "roe": None,       # ROE
            "margem_liquida": None,
            "div_liq_pat": None,  # Dívida Líquida / Patrimônio
        }

        # Tenta encontrar a tabela de indicadores
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value_str = cells[1].get_text(strip=True)

                    value = self._parse_br_number(value_str)

                    if "p/l" in label:
                        indicators["pl"] = value
                    elif "p/vp" in label:
                        indicators["pvp"] = value
                    elif "div.yield" in label:
                        # Fundamentus retorna DY como percentual (ex: 8,0 = 8%)
                        # Converte para decimal (0.08) para consistência com yfinance
                        indicators["dy"] = value / 100 if value is not None else None
                    elif "roe" in label:
                        indicators["roe"] = value
                    elif "marg. líquida" in label:
                        indicators["margem_liquida"] = value
                    elif "dív. líquida / patrimônio" in label or "div. liq. / pat." in label:
                        indicators["div_liq_pat"] = value

        return indicators

    @staticmethod
    def _parse_br_number(value: str) -> Optional[float]:
        """Converte número no formato brasileiro (ex: 1.234,56 -> 1234.56)."""
        if not value or value == "-" or value == "N/A":
            return None

        try:
            # Remove símbolos de moeda e percentual
            value = value.replace("R$", "").replace("$", "").replace("%", "").strip()
            # Remove pontos de milhar e troca vírgula por ponto
            if "," in value and "." in value:
                # Formato brasileiro: 1.234,56
                value = value.replace(".", "").replace(",", ".")
            elif "," in value:
                value = value.replace(",", ".")
            return float(value)
        except (ValueError, TypeError):
            return None

    def close(self):
        """Fecha a sessão HTTP."""
        if self._client:
            self._client.close()
            self._client = None
