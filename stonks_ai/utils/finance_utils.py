"""Utilitários para cálculos financeiros pessoais.

Funções para análise de gastos, projeções, alertas e métricas financeiras.
"""

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from stonks_ai.database import db
from stonks_ai.models.alert import Alert, AlertConfig
from stonks_ai.models.category import Category
from stonks_ai.models.financial_goal import FinancialGoal
from stonks_ai.models.transaction import Transaction


# ── Dashboard / Resumo ──────────────────────────────────────────────────

def get_month_summary(year: int, month: int) -> Dict[str, Any]:
    """
    Obtém resumo financeiro de um mês específico.

    Returns:
        Dict com: total_income, total_expense, balance, top_categories,
                 transaction_count, avg_daily_expense
    """
    start_date = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end_date = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end_date = datetime(year, month + 1, 1, tzinfo=timezone.utc)

    try:
        with db.session() as session:
            transactions_raw = session.query(Transaction).filter(
                Transaction.date >= start_date,
                Transaction.date < end_date,
            ).all()
            # Converte para dicts dentro da sessão para evitar detached errors
            transactions = [
                {
                    "amount": t.amount,
                    "type": t.type,
                    "category_name": t.category_name or "Sem categoria",
                    "date": t.date,
                }
                for t in transactions_raw
            ]
    except Exception:
        return _empty_summary()

    total_income = sum(t["amount"] for t in transactions if t["type"] == "income")
    total_expense = sum(t["amount"] for t in transactions if t["type"] == "expense")
    balance = total_income - total_expense

    # Gastos por categoria
    category_spending: Dict[str, float] = defaultdict(float)
    for t in transactions:
        if t["type"] == "expense":
            cat_name = t["category_name"]
            category_spending[cat_name] += t["amount"]

    top_categories = sorted(
        [{"name": k, "amount": v, "percent": round(v / total_expense * 100, 1) if total_expense else 0}
         for k, v in category_spending.items()],
        key=lambda x: x["amount"],
        reverse=True,
    )[:10]

    days_in_month = (end_date - start_date).days
    avg_daily_expense = round(total_expense / days_in_month, 2) if days_in_month > 0 else 0

    return {
        "total_income": round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "balance": round(balance, 2),
        "transaction_count": len(transactions),
        "avg_daily_expense": avg_daily_expense,
        "top_categories": top_categories,
        "year": year,
        "month": month,
    }


def _empty_summary() -> Dict[str, Any]:
    """Retorna resumo vazio (quando não há dados)."""
    return {
        "total_income": 0,
        "total_expense": 0,
        "balance": 0,
        "transaction_count": 0,
        "avg_daily_expense": 0,
        "top_categories": [],
        "year": datetime.now(timezone.utc).year,
        "month": datetime.now(timezone.utc).month,
    }


def get_balance_history(days: int = 90) -> List[Dict[str, Any]]:
    """
    Gera histórico de saldo acumulado ao longo do tempo.

    Args:
        days: Número de dias para analisar.

    Returns:
        Lista de {date, balance} para cada dia.
    """
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    try:
        with db.session() as session:
            transactions_raw = session.query(Transaction).filter(
                Transaction.date >= start_date,
                Transaction.date <= end_date,
            ).order_by(Transaction.date).all()
            # Converte para dicts dentro da sessão
            transactions = [
                {
                    "date": t.date,
                    "type": t.type,
                    "amount": t.amount,
                }
                for t in transactions_raw
            ]
    except Exception:
        return []

    # Acumula saldo dia a dia
    daily_balance: Dict[str, float] = defaultdict(float)
    for t in transactions:
        day_key = t["date"].strftime("%Y-%m-%d")
        if t["type"] == "income":
            daily_balance[day_key] += t["amount"]
        else:
            daily_balance[day_key] -= t["amount"]

    # Preenche todos os dias e calcula saldo acumulado
    balance_history = []
    running_balance = 0
    current = start_date

    while current <= end_date:
        day_key = current.strftime("%Y-%m-%d")
        running_balance += daily_balance.get(day_key, 0)
        balance_history.append({
            "date": day_key,
            "balance": round(running_balance, 2),
        })
        current += timedelta(days=1)

    return balance_history


# ── Alertas ─────────────────────────────────────────────────────────────

def check_and_generate_alerts() -> List[Alert]:
    """
    Verifica condições e gera alertas automaticamente.

    1. Gasto excessivo em categoria (vs mês anterior)
    2. Projeção de saldo negativo
    3. Orçamento de categoria estourado
    4. Meta em risco
    5. Assinatura com alteração de valor

    Returns:
        Lista de novos alertas gerados.
    """
    new_alerts = []

    # Carrega configs como dicts para evitar detached session errors
    try:
        with db.session() as session:
            configs_raw = session.query(AlertConfig).all()
            configs = {
                c.alert_type: {
                    "enabled": bool(c.enabled),
                    "threshold": c.threshold,
                    "min_interval_hours": c.min_interval_hours,
                }
                for c in configs_raw
            }
    except Exception:
        configs = {}

    # 1. Gasto excessivo em categoria
    new_alerts.extend(_check_spending_pattern(configs))

    # 2. Projeção de saldo negativo
    new_alerts.extend(_check_balance_low(configs))

    # 3. Orçamento estourado
    new_alerts.extend(_check_budget_exceeded(configs))

    # 4. Meta em risco
    new_alerts.extend(_check_goals_at_risk(configs))

    return new_alerts


def _check_spending_pattern(configs: Dict) -> List[Alert]:
    """Verifica aumento de gastos em categorias vs mês anterior."""
    alerts = []
    cfg = configs.get("spending_pattern")
    if not cfg or not cfg["enabled"]:
        return alerts

    now = datetime.now(timezone.utc)
    current_month = now.month
    current_year = now.year
    threshold = cfg["threshold"] or 20.0

    # Mês anterior
    if current_month == 1:
        prev_month, prev_year = 12, current_year - 1
    else:
        prev_month, prev_year = current_month - 1, current_year

    current_summary = get_month_summary(current_year, current_month)
    prev_summary = get_month_summary(prev_year, prev_month)

    if not current_summary["top_categories"] or not prev_summary["top_categories"]:
        return alerts

    # Compara categorias
    prev_cats = {c["name"]: c["amount"] for c in prev_summary["top_categories"]}

    for cat in current_summary["top_categories"]:
        if cat["name"] in prev_cats and prev_cats[cat["name"]] > 0:
            increase_pct = ((cat["amount"] - prev_cats[cat["name"]]) / prev_cats[cat["name"]]) * 100
            if increase_pct > threshold:
                alert = Alert(
                    alert_type="spending_pattern",
                    title=f"⚠️ Gasto com {cat['name']} aumentou {increase_pct:.0f}%",
                    message=(
                        f"Você gastou R$ {cat['amount']:.2f} com {cat['name']} este mês, "
                        f"contra R$ {prev_cats[cat['name']]:.2f} no mês passado "
                        f"(+{increase_pct:.0f}%)."
                    ),
                    severity="warning" if increase_pct < 50 else "critical",
                    category_id=None,
                    data=json.dumps({"category": cat["name"], "increase_pct": increase_pct}),
                )
                alerts.append(alert)

    return alerts


def _check_balance_low(configs: Dict) -> List[Alert]:
    """Projeta saldo futuro e alerta se pode ficar negativo."""
    alerts = []
    cfg = configs.get("balance_low")
    if not cfg or not cfg["enabled"]:
        return alerts

    now = datetime.now(timezone.utc)
    try:
        with db.session() as session:
            # Últimos 30 dias de transações
            start = now - timedelta(days=30)
            recent_raw = session.query(Transaction).filter(
                Transaction.date >= start,
                Transaction.date <= now,
            ).all()
            # Converte para dicts dentro da sessão
            recent = [
                {"amount": t.amount, "type": t.type}
                for t in recent_raw
            ]
    except Exception:
        return alerts

    if not recent:
        return alerts

    # Calcula gasto médio diário
    total_expense = sum(t["amount"] for t in recent if t["type"] == "expense")
    avg_daily = total_expense / 30 if total_expense > 0 else 0

    # Saldo atual (últimas transações)
    current_balance = sum(
        t["amount"] if t["type"] == "income" else -t["amount"]
        for t in recent[-30:]
    )

    # Projeta para 7 dias
    projected_balance = current_balance - (avg_daily * 7)
    if projected_balance < 0 and current_balance > 0:
        days_to_negative = int(current_balance / avg_daily) if avg_daily > 0 else 0
        if days_to_negative <= 7:
            alert = Alert(
                alert_type="balance_low",
                title="💰 Saldo pode ficar negativo",
                message=(
                    f"Com seu gasto médio de R$ {avg_daily:.2f}/dia, "
                    f"seu saldo pode ficar negativo em aproximadamente "
                    f"{days_to_negative} dias."
                ),
                severity="critical" if days_to_negative <= 3 else "warning",
                data=json.dumps({"avg_daily": avg_daily, "days_to_negative": days_to_negative}),
            )
            alerts.append(alert)

    return alerts


def _check_budget_exceeded(configs: Dict) -> List[Alert]:
    """Verifica se categorias estouraram o orçamento."""
    alerts = []
    cfg = configs.get("budget_exceeded")
    if not cfg or not cfg["enabled"]:
        return alerts

    threshold = cfg["threshold"] or 10.0
    now = datetime.now(timezone.utc)

    # Carrega categorias como dicts dentro da sessão
    try:
        with db.session() as session:
            categories_raw = session.query(Category).filter(
                Category.budget_limit.isnot(None),
                Category.budget_limit > 0,
            ).all()
            categories = [
                {"id": c.id, "name": c.name, "budget_limit": c.budget_limit}
                for c in categories_raw
            ]
    except Exception:
        return alerts

    if not categories:
        return alerts

    summary = get_month_summary(now.year, now.month)
    cat_spending = {c["name"]: c["amount"] for c in summary["top_categories"]}

    for cat in categories:
        spent = cat_spending.get(cat["name"], 0)
        budget = cat["budget_limit"] / 100.0  # Converte de centavos

        if spent > 0 and spent > budget:
            excess_pct = ((spent - budget) / budget) * 100
            if excess_pct > threshold:
                alert = Alert(
                    alert_type="budget_exceeded",
                    title=f"📊 Orçamento de {cat['name']} estourado!",
                    message=(
                        f"Você já gastou R$ {spent:.2f} de R$ {budget:.2f} "
                        f"orçados para {cat['name']} (+{excess_pct:.0f}%)."
                    ),
                    severity="warning",
                    category_id=cat["id"],
                    data=json.dumps({"category": cat["name"], "spent": spent, "budget": budget}),
                )
                alerts.append(alert)

    return alerts


def _check_goals_at_risk(configs: Dict) -> List[Alert]:
    """Verifica metas que estão atrasadas."""
    alerts = []
    cfg = configs.get("goal_at_risk")
    if not cfg or not cfg["enabled"]:
        return alerts

    # Carrega dados das metas dentro da sessão para evitar detached errors
    try:
        with db.session() as session:
            goals_raw = session.query(FinancialGoal).filter(
                FinancialGoal.status == "active",
                FinancialGoal.deadline.isnot(None),
            ).all()
            goals = [
                {
                    "id": g.id,
                    "name": g.name,
                    "progress_percent": g.progress_percent,
                    "days_remaining": g.days_remaining,
                    "remaining_amount": g.remaining_amount,
                    "is_on_track": g.is_on_track,
                }
                for g in goals_raw
            ]
    except Exception:
        return alerts

    for goal in goals:
        if not goal["is_on_track"] and goal["progress_percent"] < 100:
            alert = Alert(
                alert_type="goal_at_risk",
                title=f"🎯 Meta '{goal['name']}' está atrasada",
                message=(
                    f"Progresso: {goal['progress_percent']:.1f}% · "
                    f"Faltam {goal['days_remaining']} dias · "
                    f"R$ {goal['remaining_amount']:.2f} restantes."
                ),
                severity="warning",
                related_goal_id=goal["id"],
                data=json.dumps({
                    "goal_name": goal["name"],
                    "progress": goal["progress_percent"],
                    "remaining": goal["remaining_amount"],
                    "days_left": goal["days_remaining"],
                }),
            )
            alerts.append(alert)

    return alerts


def save_alerts(alerts: List[Alert]) -> int:
    """Salva alertas no banco (evita duplicatas recentes)."""
    saved = 0
    for alert in alerts:
        try:
            with db.session() as session:
                # Verifica se alerta similar já foi criado nas últimas 24h
                recent = session.query(Alert).filter(
                    Alert.alert_type == alert.alert_type,
                    Alert.title == alert.title,
                    Alert.created_at >= datetime.now(timezone.utc) - timedelta(hours=24),
                ).first()
                if recent:
                    continue
                session.add(alert)
                saved += 1
        except Exception:
            continue
    return saved


# ── Metas Financeiras ───────────────────────────────────────────────────

def get_goal_analysis(goal: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gera análise detalhada de uma meta financeira.

    Args:
        goal: Dict com chaves target_amount, current_amount, etc.
              (pode vir de FinancialGoal.to_dict() ou dados extraídos)

    Returns:
        Dict com: sugestão mensal, prazo estimado, cenários.
    """
    remaining = goal.get("remaining_amount", goal.get("target_amount", 0) - goal.get("current_amount", 0))
    days_left = goal.get("days_remaining", 0)
    months_left = max(1, days_left / 30)

    # Economia mensal necessária
    monthly_needed = remaining / months_left if months_left > 0 else remaining

    # Cenários
    scenarios = {
        "conservador": {
            "monthly": round(monthly_needed * 0.8, 2),
            "months": int(remaining / (monthly_needed * 0.8)) if monthly_needed * 0.8 > 0 else 0,
        },
        "realista": {
            "monthly": round(monthly_needed, 2),
            "months": int(months_left),
        },
        "agressivo": {
            "monthly": round(monthly_needed * 1.5, 2),
            "months": int(remaining / (monthly_needed * 1.5)) if monthly_needed * 1.5 > 0 else 0,
        },
    }

    return {
        "goal_name": goal.get("name", ""),
        "target": goal.get("target_amount", 0),
        "current": goal.get("current_amount", 0),
        "remaining": remaining,
        "progress": goal.get("progress_percent", 0),
        "days_left": days_left,
        "monthly_needed": round(monthly_needed, 2),
        "scenarios": scenarios,
        "is_on_track": goal.get("is_on_track", True),
    }
