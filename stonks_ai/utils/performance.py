"""
Rentabilidade da carteira ponderada no tempo, comparada com o CDI e o Ibovespa.

Explicação com exemplos em docs/CARTEIRA.md (seção 4). Resumo: para cada pregão desde a
primeira operação, o retorno do dia é

    (valor no fim do dia + vendas + proventos) / (valor do dia anterior + compras) - 1

e os retornos diários são encadeados. Aportes e resgates não contam como ganho nem perda;
o número mede só as escolhas de investimento, como a cota de um fundo.

As funções de cálculo recebem os dados prontos (testáveis sem internet); `overview` busca
preços, CDI e Ibovespa em stonks_ai/collectors/stocks/benchmarks.py.
"""

import bisect
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from dateutil.relativedelta import relativedelta

from stonks_ai.models.investment import INCOME_KINDS, InvestmentOperation
from stonks_ai.utils.portfolio import EPS, _sort_key, list_operations

IBOV_SYMBOL = "^BVSP"
# Pontos do gráfico: um por semana basta para anos de histórico
CHART_STEP = 5


def unadjust_splits(closes: Dict[date, float], splits: Dict[date, float]) -> Dict[date, float]:
    """Desfaz o ajuste do yfinance: preço antes de um desdobramento volta a ser o negociado.

    O yfinance divide os preços anteriores a um desdobramento 1:2 por 2. A carteira usa as
    cotas que existiam em cada dia, então precisa do preço daquele dia.
    """
    events = sorted(splits.items())
    out = {}
    for day, price in closes.items():
        factor = 1.0
        for split_day, ratio in events:
            if split_day > day:
                factor *= ratio
        out[day] = price * factor
    return out


def portfolio_index(ops: Iterable[InvestmentOperation], days: List[date],
                    prices: Dict[str, Dict[date, float]]) -> Tuple[List[float], List[str]]:
    """Índice da carteira (começa em 1,0) em cada dia de `days`.

    Devolve também os ativos sem nenhum preço histórico: esses são avaliados pelo preço da
    última operação (retorno zero enquanto não houver nova operação).
    """
    ops = sorted(ops, key=_sort_key)
    qty: Dict[str, float] = {}
    last_price: Dict[str, float] = {}
    without_history = sorted({op.ticker for op in ops if not prices.get(op.ticker)})

    index, value_before, i = 1.0, 0.0, 0
    out = []
    for day in days:
        buys = sells = income = 0.0
        while i < len(ops) and ops[i].date.date() <= day:
            op = ops[i]
            held = qty.get(op.ticker, 0.0)
            if op.kind == "buy":
                qty[op.ticker] = held + op.quantity
                buys += op.quantity * op.price + op.fees
                last_price.setdefault(op.ticker, op.price)
            elif op.kind == "sell":
                # Venda de cotas compradas antes do histórico: só a parte conhecida entra na conta
                known = min(op.quantity, held)
                if op.quantity > EPS:
                    sells += (op.quantity * op.price - op.fees) * known / op.quantity
                qty[op.ticker] = held - known
            elif op.kind == "bonus":
                qty[op.ticker] = held + op.quantity
            elif op.kind == "grouping":
                qty[op.ticker] = max(0.0, held - op.quantity)
            elif op.kind in INCOME_KINDS:
                income += op.amount
            if op.kind in ("buy", "sell") and op.ticker in without_history:
                last_price[op.ticker] = op.price
            i += 1

        for ticker, series in prices.items():
            if day in series:
                last_price[ticker] = series[day]
        value = sum(q * last_price.get(t, 0.0) for t, q in qty.items() if q > EPS)

        base = value_before + buys
        if base > EPS:
            index *= (value + sells + income) / base
        value_before = value
        out.append(index)
    return out, without_history


def cdi_index(days: List[date], rates: Dict[date, float]) -> List[float]:
    """CDI acumulado (começa em 1,0): a taxa de cada dia útil rende até o dia seguinte."""
    out, index = [], 1.0
    for n, day in enumerate(days):
        if n:
            prev = days[n - 1]
            # Soma as taxas dos dias úteis entre o pregão anterior e este (feriados só da B3, etc.)
            d = prev
            while d < day:
                index *= 1 + rates.get(d, 0.0) / 100
                d += timedelta(days=1)
        out.append(index)
    return out


def price_index(days: List[date], closes: Dict[date, float]) -> Optional[List[float]]:
    """Variação de um índice de preços (Ibovespa) desde o primeiro dia, preenchendo lacunas."""
    known = sorted(closes)
    if not known:
        return None
    out, base, last = [], None, None
    for day in days:
        if day in closes:
            last = closes[day]
        elif last is None:
            k = bisect.bisect_right(known, day) - 1
            last = closes[known[k]] if k >= 0 else closes[known[0]]
        if base is None:
            base = last
        out.append(last / base)
    return out


def window_return(days: List[date], index: Optional[List[float]], start: date) -> Optional[float]:
    """Retorno em % desde o fim de `start` (exclusive) até o último dia; None se a série começa depois."""
    if not index or not days or days[0] > start:
        return None
    k = bisect.bisect_right(days, start) - 1
    return round((index[-1] / index[k] - 1) * 100, 2)


def build(ops: List[InvestmentOperation], days: List[date], prices: Dict[str, Dict[date, float]],
          cdi_rates: Optional[Dict[date, float]], ibov_closes: Optional[Dict[date, float]],
          today: date) -> Dict[str, Any]:
    """Séries e resumo por período, a partir dos dados já buscados."""
    port, without_history = portfolio_index(ops, days, prices)
    cdi = cdi_index(days, cdi_rates) if cdi_rates else None
    ibov = price_index(days, ibov_closes) if ibov_closes else None

    def pct(series: Optional[List[float]], k: int) -> Optional[float]:
        return round((series[k] - 1) * 100, 2) if series else None

    picks = list(range(0, len(days), CHART_STEP))
    if picks[-1] != len(days) - 1:
        picks.append(len(days) - 1)
    chart = [{"date": days[k].isoformat(), "portfolio": pct(port, k), "cdi": pct(cdi, k), "ibov": pct(ibov, k)}
             for k in picks]

    series = {"portfolio": port, "cdi": cdi, "ibov": ibov}
    windows = []
    for key, label, start in (
        ("start", "Desde o início", None),
        ("12m", "Últimos 12 meses", today - relativedelta(months=12)),
        ("ytd", f"Em {today.year}", date(today.year - 1, 12, 31)),
    ):
        if start is None:
            # Desde o início, o primeiro dia já conta: o índice parte de 1,0 antes dele
            row = {name: pct(s, -1) for name, s in series.items()}
        else:
            row = {name: window_return(days, s, start) for name, s in series.items()}
        if row["portfolio"] is None:
            continue
        row["cdi_share"] = (round(row["portfolio"] / row["cdi"] * 100) if row["cdi"] and row["cdi"] > 0 else None)
        windows.append({"key": key, "label": label, **row})

    return {
        "start": days[0].isoformat(),
        "end": days[-1].isoformat(),
        "chart": chart,
        "windows": windows,
        "without_history": without_history,
        "benchmarks": {"cdi": cdi is not None, "ibov": ibov is not None},
    }


# ── Busca dos dados ─────────────────────────────────────────────────────

def _ticker_prices(ticker: str, start: date, fetch) -> Tuple[str, Dict[date, float]]:
    try:
        closes, splits = fetch(f"{ticker}.SA", start)
    except Exception:
        return ticker, {}
    return ticker, unadjust_splits(closes, splits)


def overview(fetch_closes: Optional[Callable] = None, fetch_cdi: Optional[Callable] = None,
             today: Optional[date] = None) -> Optional[Dict[str, Any]]:
    """Rentabilidade da carteira desde a primeira operação. None se não há operações."""
    from stonks_ai.collectors.stocks import benchmarks

    fetch_closes = fetch_closes or benchmarks.daily_closes
    fetch_cdi = fetch_cdi or benchmarks.cdi_rates
    today = today or date.today()
    ops = list_operations()
    if not ops:
        return None
    first = min(op.date.date() for op in ops)
    tickers = sorted({op.ticker for op in ops})

    with ThreadPoolExecutor(max_workers=min(8, len(tickers) + 2)) as pool:
        f_ibov = pool.submit(lambda: fetch_closes(IBOV_SYMBOL, first))
        f_cdi = pool.submit(lambda: fetch_cdi(first, today))
        prices = dict(pool.map(lambda t: _ticker_prices(t, first, fetch_closes), tickers))
        try:
            ibov_closes = f_ibov.result()[0]
        except Exception:
            ibov_closes = None
        try:
            rates = f_cdi.result()
        except Exception:
            rates = None

    # Calendário: pregões do Ibovespa; sem ele, os dias com preço de algum ativo
    if ibov_closes:
        calendar = set(ibov_closes)
    else:
        calendar = {d for series in prices.values() for d in series}
    days = sorted(d for d in calendar if first <= d <= today)
    if not days or days[-1] < today:
        days.append(today)  # operações de hoje entram mesmo antes do fechamento
    if days[0] > first:
        days.insert(0, first)
    return build(ops, days, prices, rates, ibov_closes, today)
