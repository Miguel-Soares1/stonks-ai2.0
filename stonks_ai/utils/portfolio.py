"""
Carteira de investimentos: posições calculadas a partir das operações.

Nada de posição é guardado: quantidade, preço médio, lucro realizado e proventos saem
sempre do histórico de operações (tabela investment_operations). Assim, apagar ou corrigir
uma operação antiga corrige tudo o que vem depois.

Preço médio pelo método da Receita Federal: compras somam quantidade e custo (com as taxas);
vendas tiram cotas pelo preço médio e não mudam o preço médio; desdobramento soma cotas sem
custo; bonificação soma cotas pelo custo atribuído; grupamento tira cotas sem mudar o custo.

Por enquanto só ativos da B3 (ações, FIIs, ETFs e BDRs), todos em reais.
"""

import hashlib
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from dateutil.relativedelta import relativedelta

from stonks_ai.database import db
from stonks_ai.models.investment import INCOME_KINDS, OPERATION_KINDS, InvestmentOperation

# Ações, units, FIIs, ETFs e BDRs: 4 letras e 1 ou 2 dígitos (PETR4, SANB11, HGLG11, AAPL34)
TICKER_PATTERN = re.compile(r"^[A-Z]{4}\d{1,2}$")
EPS = 1e-9
QUOTE_TTL_SECONDS = 120

# Na mesma data: compras antes das vendas (day trade), eventos antes das vendas
_DAY_ORDER = {"buy": 0, "bonus": 1, "grouping": 2, "sell": 3}


class PortfolioError(ValueError):
    """Operação inválida (mensagem pronta para mostrar ao usuário)."""


def normalize_ticker(ticker: str) -> str:
    """PETR4F (mercado fracionário) e petr4.sa viram PETR4."""
    t = ticker.strip().upper()
    if t.endswith(".SA"):
        t = t[:-3]
    m = re.match(r"^([A-Z]{4}\d{1,2})F$", t)
    return m.group(1) if m else t


def is_supported_ticker(ticker: str) -> bool:
    return bool(TICKER_PATTERN.match(ticker))


@dataclass
class Position:
    ticker: str
    quantity: float = 0.0
    cost: float = 0.0          # custo das cotas que ainda estão na carteira
    realized: float = 0.0      # lucro (ou prejuízo) das vendas
    income: float = 0.0        # proventos recebidos desde o início
    income_12m: float = 0.0    # proventos dos últimos 12 meses
    # Vendeu mais do que tinha comprado: falta lançar compras antigas (o extrato da B3 começa em 2019)
    incomplete: bool = False
    first_date: Optional[str] = None

    @property
    def avg_price(self) -> float:
        return self.cost / self.quantity if self.quantity > EPS else 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["avg_price"] = round(self.avg_price, 6)
        return d


def _sort_key(op: InvestmentOperation) -> Tuple:
    return (op.date, _DAY_ORDER.get(op.kind, 9), op.id or 0)


def build_positions(ops: Iterable[InvestmentOperation], today: Optional[date] = None,
                    sales: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Position]:
    """Aplica as operações em ordem e devolve a posição de cada ativo (inclusive as zeradas).

    Com `sales`, acrescenta nela cada venda com o custo pelo preço médio e o resultado (relatório do IR).
    """
    today = today or date.today()
    since_12m = today - relativedelta(months=12)
    positions: Dict[str, Position] = {}

    for op in sorted(ops, key=_sort_key):
        p = positions.setdefault(op.ticker, Position(ticker=op.ticker))
        day = op.date.date() if isinstance(op.date, datetime) else op.date
        if p.first_date is None:
            p.first_date = day.isoformat()

        if op.kind == "buy":
            p.quantity += op.quantity
            p.cost += op.quantity * op.price + op.fees
        elif op.kind == "sell":
            qty = op.quantity
            if qty > p.quantity + EPS:
                p.incomplete = True
                qty = p.quantity  # só dá para calcular o lucro das cotas conhecidas
            avg = p.avg_price
            sold_value = op.quantity * op.price - op.fees
            # Taxas e valor proporcionais às cotas conhecidas
            share = qty / op.quantity if op.quantity > EPS else 0.0
            p.realized += sold_value * share - qty * avg
            if sales is not None:
                sales.append({
                    "date": day, "ticker": op.ticker, "quantity": op.quantity, "known_quantity": qty,
                    "proceeds": round(sold_value, 2), "cost": round(qty * avg, 2),
                    "result": round(sold_value * share - qty * avg, 2),
                })
            p.cost -= qty * avg
            p.quantity -= qty
        elif op.kind == "bonus":
            p.quantity += op.quantity
            p.cost += op.quantity * op.price
        elif op.kind == "grouping":
            p.quantity = max(0.0, p.quantity - op.quantity)
        elif op.kind in INCOME_KINDS:
            p.income += op.amount
            if day > since_12m:
                p.income_12m += op.amount

        if p.quantity <= EPS:
            p.quantity, p.cost = 0.0, 0.0
    return positions


def income_by_month(ops: Iterable[InvestmentOperation], months: int = 12,
                    today: Optional[date] = None) -> List[Dict[str, Any]]:
    """Proventos recebidos em cada um dos últimos `months` meses (o atual incluído)."""
    today = today or date.today()
    first = date(today.year, today.month, 1) - relativedelta(months=months - 1)
    buckets = {}
    for i in range(months):
        d = first + relativedelta(months=i)
        buckets[(d.year, d.month)] = 0.0
    for op in ops:
        if op.kind in INCOME_KINDS:
            key = (op.date.year, op.date.month)
            if key in buckets:
                buckets[key] += op.amount
    return [{"year": y, "month": m, "amount": round(v, 2)} for (y, m), v in buckets.items()]


# ── Cotações ────────────────────────────────────────────────────────────

_quote_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}


def clear_quote_cache() -> None:
    _quote_cache.clear()


def _cached_quote(ticker: str, fetch: Callable[[str], Any]) -> Optional[Dict[str, Any]]:
    """Cotação com cache curto: Início e Carteira abertos em seguida não repetem a consulta."""
    hit = _quote_cache.get(ticker)
    if hit and time.monotonic() - hit[0] < QUOTE_TTL_SECONDS:
        return hit[1]
    try:
        q = fetch(ticker)
    except Exception:
        return None
    data = {"price": q.price, "change_percent": q.change_percent, "name": q.name}
    _quote_cache[ticker] = (time.monotonic(), data)
    return data


_collector = None


def _default_fetch(ticker: str):
    global _collector
    if _collector is None:
        from stonks_ai.collectors.stocks.b3 import B3Collector  # import tardio: yfinance é pesado

        _collector = B3Collector()
    return _collector.get_quote(ticker)


# ── Banco ───────────────────────────────────────────────────────────────

def list_operations(ticker: Optional[str] = None) -> List[InvestmentOperation]:
    with db.session() as s:
        q = s.query(InvestmentOperation)
        if ticker:
            q = q.filter(InvestmentOperation.ticker == normalize_ticker(ticker))
        return q.order_by(InvestmentOperation.date.desc(), InvestmentOperation.id.desc()).all()


def add_operation(ticker: str, kind: str, day: date, quantity: float = 0.0, price: float = 0.0,
                  fees: float = 0.0, amount: float = 0.0, notes: Optional[str] = None) -> InvestmentOperation:
    """Lança uma operação à mão, com as mesmas regras que valem para a importação."""
    ticker = normalize_ticker(ticker)
    if not is_supported_ticker(ticker):
        raise PortfolioError(
            f"{ticker} não é um código da B3. Por enquanto a carteira aceita ações, FIIs, ETFs e BDRs "
            "(ex.: PETR4, HGLG11, BOVA11, AAPL34)."
        )
    if kind not in OPERATION_KINDS:
        raise PortfolioError("Tipo de operação inválido.")
    if day > date.today():
        raise PortfolioError("A data da operação não pode estar no futuro.")
    if kind in INCOME_KINDS:
        if amount <= 0:
            raise PortfolioError("Informe o valor recebido.")
        quantity, price, fees = 0.0, 0.0, 0.0
    else:
        if quantity <= 0:
            raise PortfolioError("Informe a quantidade de cotas.")
        if kind in ("buy", "sell") and price <= 0:
            raise PortfolioError("Informe o preço por cota.")
        if kind == "grouping":
            price = 0.0
        amount = round(quantity * price, 2)

    if kind == "sell":
        held = build_positions(list_operations(ticker)).get(ticker)
        have = held.quantity if held else 0.0
        if quantity > have + EPS:
            raise PortfolioError(
                f"Pelas operações lançadas, você tem {have:g} cotas de {ticker}; não dá para vender "
                f"{quantity:g}. Lance antes as compras que faltam."
            )

    op = InvestmentOperation(
        ticker=ticker, kind=kind, date=datetime(day.year, day.month, day.day),
        quantity=quantity, price=price, fees=fees, amount=amount, source="manual", notes=notes,
    )
    with db.session() as s:
        s.add(op)
        s.flush()
    return op


def delete_operation(op_id: int) -> bool:
    with db.session() as s:
        op = s.get(InvestmentOperation, op_id)
        if not op:
            return False
        s.delete(op)
        return True


def row_key(parts: Iterable[Any]) -> str:
    """Chave estável de uma linha de extrato (para não importar duas vezes)."""
    return hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:64]


def save_imported(rows: List[Dict[str, Any]]) -> Tuple[int, int]:
    """Grava linhas vindas do importador da B3. Devolve (importadas, repetidas)."""
    if not rows:
        return 0, 0
    keys = [r["import_key"] for r in rows]
    with db.session() as s:
        existing = {
            k for (k,) in s.query(InvestmentOperation.import_key)
            .filter(InvestmentOperation.import_key.in_(keys)).all()
        }
        new = [r for r in rows if r["import_key"] not in existing]
        s.add_all(InvestmentOperation(source="b3", **r) for r in new)
    return len(new), len(rows) - len(new)


# ── Visão geral ─────────────────────────────────────────────────────────

def overview(fetch: Optional[Callable[[str], Any]] = None, today: Optional[date] = None) -> Dict[str, Any]:
    """Posições com cotação atual, totais da carteira e proventos por mês."""
    fetch = fetch or _default_fetch
    ops = list_operations()
    positions = build_positions(ops, today=today)
    open_pos = [p for p in positions.values() if p.quantity > EPS]

    quotes: Dict[str, Optional[Dict[str, Any]]] = {}
    if open_pos:
        with ThreadPoolExecutor(max_workers=min(8, len(open_pos))) as pool:
            for p, q in zip(open_pos, pool.map(lambda p: _cached_quote(p.ticker, fetch), open_pos)):
                quotes[p.ticker] = q

    rows = []
    market_total = 0.0
    missing_quotes = 0
    for p in open_pos:
        q = quotes.get(p.ticker)
        price = q["price"] if q and q.get("price") else None
        # Sem cotação, o ativo entra no patrimônio pelo custo (e a tela avisa)
        value = p.quantity * price if price else p.cost
        if price is None:
            missing_quotes += 1
        market_total += value
        rows.append({
            **p.to_dict(),
            "name": (q or {}).get("name") or "",
            "price": price,
            "change_percent": (q or {}).get("change_percent"),
            "market_value": round(value, 2),
            "result": round(value - p.cost, 2) if price else None,
            "result_percent": round((value - p.cost) / p.cost * 100, 2) if price and p.cost > EPS else None,
        })
    for r in rows:
        r["weight"] = round(r["market_value"] / market_total * 100, 2) if market_total > EPS else 0.0
    rows.sort(key=lambda r: r["market_value"], reverse=True)

    invested = sum(p.cost for p in open_pos)
    priced_cost = sum(p.cost for p in open_pos if quotes.get(p.ticker) and quotes[p.ticker].get("price"))
    priced_value = sum(r["market_value"] for r in rows if r["price"])
    closed = [
        {"ticker": p.ticker, "realized": round(p.realized, 2), "income": round(p.income, 2)}
        for p in positions.values() if p.quantity <= EPS
    ]
    return {
        "positions": rows,
        "closed": sorted(closed, key=lambda c: c["ticker"]),
        "totals": {
            "market_value": round(market_total, 2),
            "invested": round(invested, 2),
            "result": round(priced_value - priced_cost, 2),
            "result_percent": round((priced_value - priced_cost) / priced_cost * 100, 2) if priced_cost > EPS else None,
            "realized": round(sum(p.realized for p in positions.values()), 2),
            "income_total": round(sum(p.income for p in positions.values()), 2),
            "income_12m": round(sum(p.income_12m for p in positions.values()), 2),
            "missing_quotes": missing_quotes,
            "incomplete": sorted(p.ticker for p in positions.values() if p.incomplete),
            "operation_count": len(ops),
        },
        "income_by_month": income_by_month(ops, today=today),
    }
