"""
Utilitários de validação para inputs do usuário.

Valida tickers, comandos, números, etc.
"""

import re
from typing import Optional, Tuple


# Padrões de tickers conhecidos
TICKER_B3_PATTERN = re.compile(r"^[A-Z]{4}[0-9]{1,2}$", re.IGNORECASE)
TICKER_NYSE_PATTERN = re.compile(r"^[A-Z]{1,5}$", re.IGNORECASE)
TICKER_BR_SUFFIX = re.compile(r"^[A-Z0-9]+\.SA$", re.IGNORECASE)

# Lista de tickers B3 conhecidos (principais)
KNOWN_B3_TICKERS = {
    "PETR3", "PETR4", "VALE3", "ITUB4", "BBDC4", "B3SA3", "ABEV3",
    "WEGE3", "BBAS3", "MGLU3", "MAGALU", "VIIA3", "AMER3", "RENT3",
    "LREN3", "RAIL3", "CCRO3", "ECOR3", "SBSP3", "EGIE3", "NEOE3",
    "CMIG4", "ELET3", "ELET6", "TAEE11", "GGBR4", "CSNA3", "USIM5",
    "BRAP4", "VIVT3", "TIMS3", "OIBR3", "SUZB3", "KLBN11", "JBSS3",
    "PRIO3", "RRRP3", "HAPV3", "RADL3", "FLRY3", "QUAL3", "HYPE3",
    "ITSA4", "SANB11", "BRSR6", "ENBR3", "TOTS3", "LAME4", "PCAR3",
    "COGN3", "YDUQ3", "BRML3", "IGTA3", "BRCR11", "HGLG11", "KNRI11",
}

# Períodos válidos para yfinance
VALID_PERIODS = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}

# Intervalos válidos para yfinance
VALID_INTERVALS = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"}


def validate_ticker(ticker: str, exchange: Optional[str] = None) -> Tuple[bool, str]:
    """
    Valida um ticker de ação.

    Args:
        ticker: O ticker a ser validado.
        exchange: Bolsa esperada ('B3', 'NYSE', ou None para auto-detectar).

    Returns:
        Tuple[bool, str]: (válido, mensagem)
    """
    if not ticker or not ticker.strip():
        return False, "Ticker não pode estar vazio."

    ticker = ticker.strip().upper()

    # Remove sufixo .SA se presente para validação
    clean_ticker = ticker.replace(".SA", "")

    if exchange == "B3":
        if TICKER_B3_PATTERN.match(clean_ticker):
            return True, "Ticker B3 válido."
        return False, (
            f"Ticker B3 inválido: '{ticker}'. "
            f"Formato esperado: 4 letras + número (ex: PETR4, VALE3)"
        )

    elif exchange == "NYSE":
        if TICKER_NYSE_PATTERN.match(clean_ticker):
            return True, "Ticker NYSE/Nasdaq válido."
        return False, (
            f"Ticker inválido: '{ticker}'. "
            f"Formato esperado: 1 a 5 letras (ex: AAPL, MSFT, GOOGL)"
        )

    # Auto-detecção
    if TICKER_B3_PATTERN.match(clean_ticker) or TICKER_BR_SUFFIX.match(ticker):
        return True, "Parece ser um ticker da B3."
    elif TICKER_NYSE_PATTERN.match(clean_ticker):
        return True, "Parece ser um ticker da NYSE/Nasdaq."
    else:
        return False, f"Formato de ticker não reconhecido: '{ticker}'."


def detect_exchange(ticker: str) -> str:
    """
    Detecta automaticamente a bolsa baseado no formato do ticker.

    Args:
        ticker: O ticker para detectar.

    Returns:
        str: 'B3', 'NYSE', ou 'UNKNOWN'
    """
    ticker = ticker.strip().upper()

    if ticker.endswith(".SA") or TICKER_B3_PATTERN.match(ticker):
        return "B3"
    elif TICKER_NYSE_PATTERN.match(ticker):
        return "NYSE"
    else:
        return "UNKNOWN"


def validate_period(period: str) -> Tuple[bool, str]:
    """Valida período para consulta de histórico."""
    period = period.strip().lower()
    if period in VALID_PERIODS:
        return True, ""
    return False, (
        f"Período inválido: '{period}'. "
        f"Válidos: {', '.join(sorted(VALID_PERIODS))}"
    )


def validate_interval(interval: str) -> Tuple[bool, str]:
    """Valida intervalo para consulta de histórico."""
    interval = interval.strip().lower()
    if interval in VALID_INTERVALS:
        return True, ""
    return False, (
        f"Intervalo inválido: '{interval}'. "
        f"Válidos: {', '.join(sorted(VALID_INTERVALS))}"
    )


def validate_br_currency(value: str) -> Optional[float]:
    """Valida e converte string de valor monetário brasileiro para float."""
    if not value:
        return None

    try:
        # Remove R$, espaços, troca vírgula por ponto
        cleaned = value.replace("R$", "").replace(" ", "").strip()
        if "," in cleaned and "." in cleaned:
            # 1.234,56 -> 1234.56
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def validate_yes_no(value: str) -> Optional[bool]:
    """Valida resposta sim/não."""
    v = value.strip().lower()
    if v in ("s", "sim", "yes", "y", ""):
        return True
    elif v in ("n", "nao", "não", "no"):
        return False
    return None
