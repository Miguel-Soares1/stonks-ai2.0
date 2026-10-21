"""
Criptomoedas da carteira: as moedas aceitas, a cotação e o histórico em reais.

O Yahoo Finance não tem mais os pares em reais (BTC-BRL não existe); o app usa os pares em
dólar (BTC-USD) e o câmbio do dólar (BRL=X). Preço em reais = preço em dólar × câmbio do mesmo
dia. Cripto negocia todo dia e o câmbio só em dia útil: no fim de semana vale o câmbio de sexta.

Só as moedas da lista: o símbolo no Yahoo de moedas menores muda (UNI virou UNI7083-USD) e um
código errado viraria outra moeda sem ninguém perceber.
"""

import bisect
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable, Dict, Tuple

ASSETS = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "SOL": "Solana",
    "XRP": "XRP",
    "BNB": "BNB",
    "ADA": "Cardano",
    "DOGE": "Dogecoin",
    "LTC": "Litecoin",
    "LINK": "Chainlink",
    "AVAX": "Avalanche",
    "DOT": "Polkadot",
    "TRX": "TRON",
    "BCH": "Bitcoin Cash",
    "XLM": "Stellar",
    "SHIB": "Shiba Inu",
    "ATOM": "Cosmos",
    "NEAR": "NEAR Protocol",
    "USDT": "Tether (USDT)",
    "USDC": "USD Coin",
}
STABLECOINS = {"USDT", "USDC"}
FX_SYMBOL = "BRL=X"


class CryptoError(Exception):
    """Cotação indisponível (sem internet, Yahoo fora do ar)."""


@dataclass
class CryptoQuote:
    price: float
    change_percent: float
    name: str


def is_crypto(ticker: str) -> bool:
    return ticker in ASSETS


def yahoo_symbol(ticker: str) -> str:
    return f"{ticker}-USD"


def to_brl(usd: Dict[date, float], fx: Dict[date, float]) -> Dict[date, float]:
    """Converte cada fechamento pelo câmbio do mesmo dia ou do último dia útil antes dele."""
    fx_days = sorted(fx)
    out = {}
    for day, price in usd.items():
        k = bisect.bisect_right(fx_days, day) - 1
        if k >= 0:
            out[day] = price * fx[fx_days[k]]
    return out


def daily_closes_brl(ticker: str, start: date,
                     fetch: Callable[[str, date], Tuple[Dict[date, float], Dict[date, float]]]) -> Dict[date, float]:
    """Fechamentos diários em reais desde start. fetch é benchmarks.daily_closes (ou um falso nos testes)."""
    usd, _ = fetch(yahoo_symbol(ticker), start)
    # Uma semana antes: se start cai num fim de semana, o câmbio vem da sexta anterior
    fx, _ = fetch(FX_SYMBOL, start - timedelta(days=7))
    return to_brl(usd, fx)


def _closes(symbol: str) -> Dict[date, float]:
    import yfinance as yf  # import tardio: pesado

    hist = yf.Ticker(symbol).history(period="7d", auto_adjust=False)
    if hist is None or hist.empty:
        raise CryptoError(f"Sem cotação de {symbol}.")
    return {ts.date(): float(v) for ts, v in hist["Close"].items() if v == v and v > 0}


def get_quote(ticker: str) -> CryptoQuote:
    """Cotação agora em reais e a variação desde o fechamento do dia anterior (00h UTC)."""
    if not is_crypto(ticker):
        raise CryptoError(f"{ticker} não está na lista de criptomoedas.")
    try:
        brl = to_brl(_closes(yahoo_symbol(ticker)), _closes(FX_SYMBOL))
    except CryptoError:
        raise
    except Exception as e:
        raise CryptoError(f"Não foi possível buscar a cotação de {ticker}: {e}")
    days = sorted(brl)
    if not days:
        raise CryptoError(f"Sem cotação de {ticker}.")
    price = brl[days[-1]]
    prev = brl[days[-2]] if len(days) > 1 else price
    return CryptoQuote(price=price, change_percent=round((price / prev - 1) * 100, 2), name=ASSETS[ticker])
