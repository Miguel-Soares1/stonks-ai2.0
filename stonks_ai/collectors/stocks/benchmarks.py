"""Séries históricas para a rentabilidade da carteira: CDI diário e fechamentos diários.

- CDI: série 12 do Banco Central (SGS), taxa em % ao dia. Dado público; nada do usuário é enviado.
- Fechamentos: yfinance, com os desdobramentos/bonificações à parte (o preço que o yfinance
  devolve já vem dividido por eles; quem desfaz o ajuste é stonks_ai/utils/performance.py).

Cache em memória por uma hora: abrir a Carteira de novo não repete as consultas.
"""

import time
from datetime import date, datetime, timedelta
from typing import Dict, Tuple

import httpx

CACHE_SECONDS = 3600
BCB_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados"
# O Banco Central limita consultas de séries diárias a 10 anos; 5 por pedido dá folga
_BCB_CHUNK_DAYS = 5 * 365

_cache: Dict[Tuple, Tuple[float, object]] = {}


class BenchmarkError(Exception):
    """Falha ao buscar uma série histórica (sem internet, serviço fora do ar)."""


def clear_cache() -> None:
    _cache.clear()


def _cached(key: Tuple, load):
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
        return hit[1]
    value = load()
    _cache[key] = (time.monotonic(), value)
    return value


def cdi_rates(start: date, end: date) -> Dict[date, float]:
    """Taxa do CDI de cada dia útil entre start e end, em % ao dia (ex.: 0.0507)."""

    def load() -> Dict[date, float]:
        rates: Dict[date, float] = {}
        chunk_start = start
        try:
            with httpx.Client(timeout=30) as client:
                while chunk_start <= end:
                    chunk_end = min(end, chunk_start + timedelta(days=_BCB_CHUNK_DAYS))
                    r = client.get(BCB_URL, params={
                        "formato": "json",
                        "dataInicial": chunk_start.strftime("%d/%m/%Y"),
                        "dataFinal": chunk_end.strftime("%d/%m/%Y"),
                    })
                    # Sem nenhum dia útil no intervalo, o Banco Central responde 404
                    if r.status_code != 404:
                        r.raise_for_status()
                        for row in r.json():
                            day = datetime.strptime(row["data"], "%d/%m/%Y").date()
                            rates[day] = float(row["valor"])
                    chunk_start = chunk_end + timedelta(days=1)
        except (httpx.HTTPError, ValueError, KeyError) as e:
            raise BenchmarkError(f"Não foi possível buscar o CDI no Banco Central: {e}")
        return rates

    return _cached(("cdi", start, end), load)


def daily_closes(symbol: str, start: date) -> Tuple[Dict[date, float], Dict[date, float]]:
    """Fechamentos diários desde start e os desdobramentos (data -> fator, ex.: 2.0 em 1:2).

    symbol no formato do yfinance: "PETR4.SA", "^BVSP".
    """

    def load():
        import yfinance as yf  # import tardio: pesado e só usado aqui

        try:
            hist = yf.Ticker(symbol).history(start=start.isoformat(), auto_adjust=False, actions=True)
        except Exception as e:
            raise BenchmarkError(f"Não foi possível buscar o histórico de {symbol}: {e}")
        if hist is None or hist.empty:
            raise BenchmarkError(f"Sem histórico de preços para {symbol}.")
        closes = {ts.date(): float(v) for ts, v in hist["Close"].items() if v == v and v > 0}
        splits = {}
        if "Stock Splits" in hist:
            splits = {ts.date(): float(v) for ts, v in hist["Stock Splits"].items() if v and v == v}
        return closes, splits

    return _cached(("closes", symbol, start), load)
