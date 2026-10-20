"""Rotas de finanças pessoais: início, transações, importação, orçamento, contas, metas e alertas."""

import calendar
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from desktop.state import personal_agent
from desktop.streaming import require_llm, stream_text
from stonks_ai.collectors.finance.categorizer import Categorizer
from stonks_ai.llm.base import LLMError
from stonks_ai.llm.client import get_local_llm_client
from stonks_ai.utils import insights, recurrence
from stonks_ai.utils.finance_utils import get_month_summary, get_multi_month_summary

router = APIRouter(prefix="/api")

TxType = Literal["expense", "income"]
Frequency = Literal["weekly", "biweekly", "monthly", "yearly"]
IMPORT_SUFFIXES = {".csv", ".xlsx", ".xls", ".pdf"}
MAX_IMPORT_BYTES = 20 * 1024 * 1024


def _not_found(what: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{what} não encontrada.")


def _until_today(year: int, month: int) -> Optional[datetime]:
    """No mês em andamento, os totais param em hoje: o que está agendado ainda não saiu."""
    now = datetime.now()
    if (year, month) != (now.year, now.month):
        return None
    return datetime(now.year, now.month, now.day, tzinfo=timezone.utc) + timedelta(days=1)


# ── Início ──────────────────────────────────────────────────────────────

@router.get("/dashboard")
def dashboard(year: Optional[int] = None, month: Optional[int] = None) -> Dict[str, Any]:
    """Resumo do mês, mês anterior (para comparação), saldo em 90 dias, metas e alertas."""
    now = datetime.now()
    year = year or now.year
    month = month or now.month
    if not 1 <= month <= 12:
        raise HTTPException(status_code=422, detail="Mês inválido.")

    # O app pode ficar aberto de um dia para o outro: cria as recorrentes que venceram
    recurrence.generate_due()
    data = personal_agent().get_dashboard(year, month)
    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    days_in_month = calendar.monthrange(year, month)[1]

    # Dia de referência para o "ritmo do mês": hoje no mês atual, mês completo no passado
    if (year, month) == (now.year, now.month):
        day = now.day
    elif (year, month) < (now.year, now.month):
        day = days_in_month
    else:
        day = 0

    summary = data["summary"]
    until = _until_today(year, month)
    if until:
        summary = get_month_summary(year, month, until=until)
    full = data["summary"]

    return {
        "period": {"year": year, "month": month, "days_in_month": days_in_month, "day": day},
        "summary": summary,
        # Lançado com data futura dentro do mês (contas agendadas, recorrentes)
        "scheduled": {
            "income": round(full["total_income"] - summary["total_income"], 2),
            "expense": round(full["total_expense"] - summary["total_expense"], 2),
        },
        "previous": get_month_summary(prev_year, prev_month),
        "balance_history": data["balance_history"],
        "goals": data["active_goals"],
        "alerts": data["active_alerts"],
        # 31 dias: uma conta mensal sempre aparece, mesmo no dia em que acabou de ser lançada
        "upcoming_recurring": recurrence.upcoming(days=31),
        "insights": insights.month_insights(year, month),
        "accounts_total": round(sum(a.get("balance") or 0 for a in personal_agent().list_accounts(active_only=True)), 2),
    }


@router.get("/months")
def months(count: int = 6) -> List[Dict[str, Any]]:
    """Resumo dos últimos meses (do mais antigo ao atual), para o gráfico de receitas e despesas."""
    return get_multi_month_summary(max(1, min(count, 24)))


@router.get("/dashboard/summary-ai")
def dashboard_summary_ai(year: int, month: int):
    """Resumo do mês escrito pela IA, em streaming."""
    agent = personal_agent()
    require_llm(agent.llm)
    summary = get_month_summary(year, month, until=_until_today(year, month))
    if not summary["transaction_count"]:
        raise HTTPException(status_code=422, detail="Não há transações neste mês para resumir.")
    prompt = agent.build_monthly_summary_prompt(year, month, summary)
    return stream_text(lambda: agent.llm.generate_stream(prompt))


# ── Transações ──────────────────────────────────────────────────────────

class TransactionIn(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    amount: float = Field(gt=0)
    type: TxType = "expense"
    category_name: Optional[str] = None
    date: Optional[str] = None  # AAAA-MM-DD
    account_id: Optional[int] = None
    notes: Optional[str] = None
    # None = não repete. Na edição, vale para a série inteira.
    recurring_frequency: Optional[Frequency] = None


@router.get("/transactions")
def transactions(
    days: Optional[int] = 30,
    type: Optional[TxType] = None,
    account_id: Optional[int] = None,
    category_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    return personal_agent().list_transactions(
        limit=min(limit, 500), offset=offset, days=days or None,
        transaction_type=type, account_id=account_id, category_id=category_id,
    )


@router.post("/transactions", status_code=201)
def transaction_add(body: TransactionIn) -> Dict[str, Any]:
    return personal_agent().add_transaction(
        description=body.description.strip(), amount=body.amount, date=body.date,
        tx_type=body.type, category_name=body.category_name or None,
        account_id=body.account_id, notes=body.notes or None,
        recurring_frequency=body.recurring_frequency,
    )


@router.put("/transactions/{tx_id}")
def transaction_update(tx_id: int, body: TransactionIn) -> Dict[str, Any]:
    updated = personal_agent().update_transaction(
        transaction_id=tx_id, description=body.description.strip(), amount=body.amount,
        tx_type=body.type, category_name=body.category_name or None,
        date=body.date, notes=body.notes or None,
        recurring_frequency=body.recurring_frequency,
    )
    if not updated:
        raise _not_found("Transação")
    return updated


@router.delete("/transactions/{tx_id}", status_code=204)
def transaction_delete(tx_id: int) -> None:
    if not personal_agent().delete_transaction(tx_id):
        raise _not_found("Transação")


@router.post("/import")
async def import_statement(request: Request, filename: str) -> Dict[str, Any]:
    """Importa um extrato. O corpo da requisição é o próprio arquivo."""
    suffix = Path(filename).suffix.lower()
    if suffix not in IMPORT_SUFFIXES:
        raise HTTPException(status_code=422, detail="Formato não suportado. Use CSV, Excel (.xlsx/.xls) ou PDF.")
    content = await request.body()
    if not content:
        raise HTTPException(status_code=422, detail="O arquivo está vazio.")
    if len(content) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo maior que 20 MB.")

    # Mantém o nome original: o importador detecta o banco por ele (ex.: "nubank-out.csv")
    safe_name = re.sub(r"[^\w.\- ]", "_", Path(filename).name)[:120]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / safe_name
        path.write_bytes(content)
        return personal_agent().import_file(str(path))


# ── Categorias e orçamento ──────────────────────────────────────────────

class BudgetIn(BaseModel):
    limit: float = Field(ge=0)


@router.get("/categories")
def categories() -> List[Dict[str, Any]]:
    return personal_agent().list_categories()


@router.get("/budget")
def budget(year: Optional[int] = None, month: Optional[int] = None) -> Dict[str, Any]:
    now = datetime.now()
    return personal_agent().get_budget_overview(year or now.year, month or now.month)


@router.get("/category-rules")
def category_rules() -> List[Dict[str, str]]:
    """Regras do usuário (correções) e da IA (estabelecimento -> categoria)."""
    return Categorizer.list_rules()


@router.delete("/category-rules/{merchant}", status_code=204)
def category_rule_delete(merchant: str) -> None:
    if not Categorizer.delete_rule(merchant):
        raise _not_found("Regra")


@router.get("/categorize-ai")
def categorize_ai_pending() -> Dict[str, int]:
    """Quantos estabelecimentos em "Outros" a IA ainda pode organizar."""
    return personal_agent().categorizer.pending_for_llm()


@router.post("/categorize-ai")
def categorize_ai_run() -> Dict[str, Any]:
    """Organiza um lote de estabelecimentos de "Outros" com a IA. O app chama até acabar.

    Sempre a IA local: descrição de extrato não vai para a nuvem, mesmo com o chat
    configurado para uma IA remota.
    """
    llm = get_local_llm_client()
    if not llm.is_available():
        raise HTTPException(
            status_code=503,
            detail="Organizar com IA usa a IA local para o extrato não sair do computador. Abra o Ollama e tente de novo.",
        )
    try:
        return personal_agent().categorizer.categorize_others_with_llm(llm)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=f"A IA falhou: {e}")


@router.put("/categories/{category_id}/budget")
def set_budget(category_id: int, body: BudgetIn) -> Dict[str, Any]:
    updated = personal_agent().set_category_budget(category_id, body.limit)
    if not updated:
        raise _not_found("Categoria")
    return updated


# ── Contas ──────────────────────────────────────────────────────────────

AccountType = Literal["checking", "savings", "credit_card", "investment", "cash", "other"]


class AccountIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    account_type: AccountType = "checking"
    balance: float = 0.0
    notes: Optional[str] = None


@router.get("/accounts")
def accounts() -> List[Dict[str, Any]]:
    return personal_agent().list_accounts(active_only=True)


@router.post("/accounts", status_code=201)
def account_add(body: AccountIn) -> Dict[str, Any]:
    return personal_agent().create_account(
        name=body.name.strip(), account_type=body.account_type,
        balance=body.balance, notes=body.notes or None,
    )


@router.put("/accounts/{account_id}")
def account_update(account_id: int, body: AccountIn) -> Dict[str, Any]:
    updated = personal_agent().update_account(
        account_id=account_id, name=body.name.strip(), account_type=body.account_type,
        balance=body.balance, notes=body.notes or None,
    )
    if not updated:
        raise _not_found("Conta")
    return updated


@router.delete("/accounts/{account_id}", status_code=204)
def account_delete(account_id: int) -> None:
    if not personal_agent().delete_account(account_id):
        raise _not_found("Conta")


# ── Metas ───────────────────────────────────────────────────────────────

GoalType = Literal["savings", "emergency", "purchase", "investment", "debt", "custom"]
Priority = Literal["low", "medium", "high"]


class GoalIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    target_amount: float = Field(gt=0)
    deadline: Optional[str] = None  # AAAA-MM-DD
    goal_type: GoalType = "savings"
    priority: Priority = "medium"
    description: Optional[str] = None
    status: Optional[Literal["active", "completed", "cancelled", "paused"]] = None


class ContributionIn(BaseModel):
    amount: float = Field(gt=0)


@router.get("/goals")
def goals(status: Optional[str] = "active") -> List[Dict[str, Any]]:
    return personal_agent().list_goals(status=None if status == "all" else status)


@router.post("/goals", status_code=201)
def goal_add(body: GoalIn) -> Dict[str, Any]:
    return personal_agent().create_goal(
        name=body.name.strip(), target_amount=body.target_amount, deadline=body.deadline or None,
        goal_type=body.goal_type, priority=body.priority, description=body.description or None,
    )


@router.put("/goals/{goal_id}")
def goal_update(goal_id: int, body: GoalIn) -> Dict[str, Any]:
    updated = personal_agent().update_goal(
        goal_id=goal_id, name=body.name.strip(), target_amount=body.target_amount,
        deadline=body.deadline or None, goal_type=body.goal_type, priority=body.priority,
        description=body.description or None, status=body.status,
    )
    if not updated:
        raise _not_found("Meta")
    return updated


@router.post("/goals/{goal_id}/contribute")
def goal_contribute(goal_id: int, body: ContributionIn) -> Dict[str, Any]:
    return personal_agent().contribute_to_goal(goal_id, body.amount)


@router.delete("/goals/{goal_id}", status_code=204)
def goal_delete(goal_id: int) -> None:
    if not personal_agent().delete_goal(goal_id):
        raise _not_found("Meta")


# ── Alertas ─────────────────────────────────────────────────────────────

@router.get("/alerts")
def alerts(include_dismissed: bool = False) -> List[Dict[str, Any]]:
    return personal_agent().list_alerts(active_only=not include_dismissed)


@router.post("/alerts/check")
def alerts_check() -> Dict[str, int]:
    return {"created": len(personal_agent().check_alerts())}


@router.post("/alerts/{alert_id}/dismiss", status_code=204)
def alert_dismiss(alert_id: int) -> None:
    if not personal_agent().dismiss_alert(alert_id):
        raise _not_found("Alerta")
