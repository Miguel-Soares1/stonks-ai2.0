"""
Transações recorrentes (aluguel, salário, assinaturas).

Uma série é o conjunto de transações com o mesmo recurrence_id. A primeira define o dia
de referência (ex.: todo dia 5); a mais recente serve de modelo para as próximas, então
editar o valor da última vale daqui para frente. As ocorrências são criadas quando a data
chega (ao abrir o app ou o Início), nunca adiantadas.

A data da última ocorrência gerada fica em user_preferences ("recurrence_last:<id>"):
assim, se o usuário excluir uma ocorrência, ela não é recriada.
"""

import uuid
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from dateutil.relativedelta import relativedelta

from stonks_ai.database import db
from stonks_ai.models.transaction import Transaction
from stonks_ai.models.user_preferences import UserPreference

FREQUENCIES = ("weekly", "biweekly", "monthly", "yearly")
FREQUENCY_LABELS = {
    "weekly": "Toda semana",
    "biweekly": "A cada 2 semanas",
    "monthly": "Todo mês",
    "yearly": "Todo ano",
}

# Teto de segurança: um app fechado por anos não cria milhares de transações de uma vez
MAX_CATCH_UP = 60
PREF_PREFIX = "recurrence_last:"


def new_recurrence_id() -> str:
    return uuid.uuid4().hex


def occurrence(anchor: date, frequency: str, n: int) -> date:
    """n-ésima data da série a partir da primeira (n=0 é a própria âncora)."""
    if frequency == "weekly":
        return anchor + timedelta(weeks=n)
    if frequency == "biweekly":
        return anchor + timedelta(weeks=2 * n)
    if frequency == "monthly":
        # relativedelta a partir da âncora mantém o dia 31 nos meses que têm 31
        return anchor + relativedelta(months=n)
    if frequency == "yearly":
        return anchor + relativedelta(years=n)
    raise ValueError(f"Frequência inválida: {frequency}")


def _as_date(value: Any) -> date:
    return value.date() if isinstance(value, datetime) else value


def _series(session) -> Dict[str, List[Transaction]]:
    rows = (
        session.query(Transaction)
        .filter(Transaction.is_recurring == 1, Transaction.recurrence_id.isnot(None))
        .order_by(Transaction.date)
        .all()
    )
    groups: Dict[str, List[Transaction]] = {}
    for tx in rows:
        groups.setdefault(tx.recurrence_id, []).append(tx)
    return groups


def _next_after(anchor: date, frequency: str, after: date) -> date:
    n = 1
    while True:
        d = occurrence(anchor, frequency, n)
        if d > after:
            return d
        n += 1


def generate_due(today: Optional[date] = None) -> int:
    """Cria as ocorrências cuja data já chegou. Devolve quantas foram criadas."""
    today = today or date.today()
    created = 0
    with db.session() as session:
        prefs = {
            p.key: p for p in session.query(UserPreference)
            .filter(UserPreference.key.like(f"{PREF_PREFIX}%")).all()
        }
        for rid, txs in _series(session).items():
            template = txs[-1]
            frequency = template.recurring_frequency
            if frequency not in FREQUENCIES:
                continue
            anchor = _as_date(txs[0].date)
            last = _as_date(template.date)
            pref = prefs.get(PREF_PREFIX + rid)
            if pref:
                last = max(last, date.fromisoformat(pref.value))

            new_last = last
            for _ in range(MAX_CATCH_UP):
                due = _next_after(anchor, frequency, new_last)
                if due > today:
                    break
                session.add(Transaction(
                    description=template.description,
                    amount=template.amount,
                    type=template.type,
                    category_id=template.category_id,
                    category_name=template.category_name,
                    account_id=template.account_id,
                    date=datetime.combine(due, datetime.min.time()),
                    source="recurring",
                    is_recurring=1,
                    recurring_frequency=frequency,
                    recurrence_id=rid,
                    notes=template.notes,
                ))
                new_last = due
                created += 1

            if new_last != last or not pref:
                if pref:
                    pref.value = new_last.isoformat()
                else:
                    session.add(UserPreference(key=PREF_PREFIX + rid, value=new_last.isoformat()))
    return created


def upcoming(days: int = 30, today: Optional[date] = None) -> List[Dict[str, Any]]:
    """Próxima ocorrência de cada série nos próximos `days` dias, por data."""
    today = today or date.today()
    limit = today + timedelta(days=days)
    result = []
    with db.session() as session:
        for rid, txs in _series(session).items():
            template = txs[-1]
            frequency = template.recurring_frequency
            if frequency not in FREQUENCIES:
                continue
            due = _next_after(_as_date(txs[0].date), frequency, max(_as_date(template.date), today - timedelta(days=1)))
            if due <= limit:
                result.append({
                    "recurrence_id": rid,
                    "description": template.description,
                    "amount": template.amount,
                    "type": template.type,
                    "category_name": template.category_name or "Sem categoria",
                    "date": due.isoformat(),
                    "frequency": frequency,
                    "frequency_label": FREQUENCY_LABELS[frequency],
                })
    return sorted(result, key=lambda r: r["date"])


def stop_series(session, recurrence_id: str) -> None:
    """Para de repetir: o histórico fica, mas nenhuma ocorrência nova é criada."""
    session.query(Transaction).filter(Transaction.recurrence_id == recurrence_id).update(
        {Transaction.is_recurring: 0}, synchronize_session=False
    )


def set_series_frequency(session, recurrence_id: str, frequency: str) -> None:
    session.query(Transaction).filter(Transaction.recurrence_id == recurrence_id).update(
        {Transaction.is_recurring: 1, Transaction.recurring_frequency: frequency},
        synchronize_session=False,
    )
