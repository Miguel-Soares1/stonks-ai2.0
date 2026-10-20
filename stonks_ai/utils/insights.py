"""
Insights do mês calculados pelo código (o valor nunca vem da IA).

A IA só entra depois, se o usuário pedir para explicar: o número mostrado na tela já
está calculado aqui, então um modelo pequeno não tem como inventá-lo.

No mês atual, a comparação é justa: os primeiros N dias deste mês contra os mesmos
N dias do mês anterior (não contra o mês anterior inteiro).
"""

import calendar
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from stonks_ai.database import db
from stonks_ai.models.category import Category
from stonks_ai.models.transaction import Transaction

# Abaixo disso, a variação é ruído
MIN_INCREASE = 50.0
MIN_INCREASE_PCT = 20.0
MIN_NEW_CATEGORY = 100.0


def _expenses_by_category(start: date, end: date) -> Dict[str, float]:
    """Despesas por categoria em [start, end)."""
    totals: Dict[str, float] = defaultdict(float)
    with db.session() as session:
        rows = session.query(Transaction.category_name, Transaction.amount).filter(
            Transaction.type == "expense",
            Transaction.date >= datetime.combine(start, datetime.min.time()),
            Transaction.date < datetime.combine(end, datetime.min.time()),
        ).all()
    for name, amount in rows:
        totals[name or "Sem categoria"] += amount
    return totals


def _month_name(month: int) -> str:
    return ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
            "agosto", "setembro", "outubro", "novembro", "dezembro"][month - 1]


def _brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def month_insights(year: int, month: int, today: Optional[date] = None) -> List[Dict[str, Any]]:
    """Até dois insights: a categoria que mais subiu e o orçamento que vai estourar."""
    today = today or date.today()
    start = date(year, month, 1)
    days_in_month = calendar.monthrange(year, month)[1]
    is_current = (year, month) == (today.year, today.month)
    if start > today:
        return []
    elapsed = today.day if is_current else days_in_month

    prev_start = (start - timedelta(days=1)).replace(day=1)
    prev_days = calendar.monthrange(prev_start.year, prev_start.month)[1]
    current = _expenses_by_category(start, start + timedelta(days=elapsed))
    previous = _expenses_by_category(prev_start, prev_start + timedelta(days=min(elapsed, prev_days)))

    insights: List[Dict[str, Any]] = []
    prev_name = _month_name(prev_start.month)
    scope = f"nos mesmos {elapsed} dias de {prev_name}" if is_current else f"em {prev_name}"

    # 1. Categoria com o maior aumento em reais
    best = None
    for cat, amount in current.items():
        before = previous.get(cat, 0.0)
        diff = amount - before
        if before > 0:
            pct = diff / before * 100
            if diff >= MIN_INCREASE and pct >= MIN_INCREASE_PCT and (not best or diff > best[1]):
                best = (cat, diff, pct, before, amount)
        elif amount >= MIN_NEW_CATEGORY and (not best or amount > best[1]):
            best = (cat, amount, None, 0.0, amount)
    if best:
        cat, diff, pct, before, amount = best
        message = (
            f"Você gastou {_brl(amount)} com {cat}, contra {_brl(before)} {scope}."
            if pct is not None else
            f"Você gastou {_brl(amount)} com {cat}, e não tinha gastos nessa categoria {scope}."
        )
        insights.append({
            "kind": "category_increase",
            "category": cat,
            "amount": round(diff, 2),
            "percent": round(pct, 1) if pct is not None else None,
            "headline": f"{_brl(diff)} a mais com {cat}",
            "message": message,
            "question": (
                f"Meus gastos com {cat} foram de {_brl(before)} para {_brl(amount)} {scope}. "
                f"Que formas práticas existem de reduzir esse tipo de gasto?"
            ),
        })

    # 2. Orçamento que vai estourar no ritmo atual (só faz sentido no mês em andamento)
    if is_current:
        with db.session() as session:
            limits = {
                c.name: c.budget_limit / 100.0
                for c in session.query(Category).filter(Category.budget_limit > 0).all()
            }
        worst = None
        for cat, limit in limits.items():
            spent = current.get(cat, 0.0)
            projected = spent / elapsed * days_in_month
            over = projected - limit
            if over > 0 and (not worst or over > worst[1]):
                worst = (cat, over, spent, limit, projected)
        if worst:
            cat, over, spent, limit, projected = worst
            already = spent >= limit
            insights.append({
                "kind": "budget_pace",
                "category": cat,
                "amount": round(over, 2),
                "percent": None,
                "headline": f"{cat} {'já passou' if already else 'vai passar'} do limite",
                "message": (
                    f"Já foram {_brl(spent)} de um limite de {_brl(limit)}."
                    if already else
                    f"Já foram {_brl(spent)} de {_brl(limit)}. No ritmo atual, o mês fecha em "
                    f"{_brl(projected)}, {_brl(over)} acima do limite."
                ),
                "question": (
                    f"Meu limite para {cat} é {_brl(limit)} por mês e já gastei {_brl(spent)} "
                    f"em {elapsed} dias. Como posso segurar esse gasto até o fim do mês?"
                ),
            })
    return insights
