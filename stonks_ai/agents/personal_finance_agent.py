"""Agente de finanças pessoais.

Gerencia transações financeiras, categorização automática, importação
de extratos, metas financeiras e alertas inteligentes.

Integra-se com:
- Coletores financeiros (CSV, Excel, PDF)
- Categorizador automático (regex + IA)
- Utilitários financeiros (cálculos, projeções, alertas)
- LLM local (Ollama) para análises avançadas
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from stonks_ai.agents.base_agent import AgentError, BaseAgent
from stonks_ai.collectors.finance.base import FinanceDataError
from stonks_ai.collectors.finance.categorizer import Categorizer
from stonks_ai.collectors.finance.csv_importer import CSVImporter
from stonks_ai.collectors.finance.excel_importer import ExcelImporter
from stonks_ai.collectors.finance.pdf_importer import PDFImporter
from stonks_ai.database import DatabaseError, db
from stonks_ai.llm.prompts import format_goal_prompt, format_monthly_summary_prompt
from stonks_ai.models.alert import Alert, AlertConfig, DEFAULT_ALERT_CONFIGS
from stonks_ai.models.account import Account, DEFAULT_ACCOUNTS
from stonks_ai.models.category import Category, DEFAULT_CATEGORIES
from stonks_ai.models.financial_goal import FinancialGoal
from stonks_ai.models.transaction import Transaction
from stonks_ai.utils.finance_utils import (
    check_and_generate_alerts,
    get_balance_history,
    get_budget_overview,
    get_goal_analysis,
    get_month_summary,
    get_multi_month_summary,
    save_alerts,
)


class PersonalFinanceAgent(BaseAgent):
    """Agente especializado em finanças pessoais."""

    def __init__(self):
        super().__init__()
        self.categorizer = Categorizer()
        self.csv_importer = CSVImporter()
        self.excel_importer = ExcelImporter()
        self.pdf_importer = PDFImporter()

    # ── Inicialização ────────────────────────────────────────────────

    def initialize(self) -> Dict[str, Any]:
        """
        Inicializa o módulo de finanças pessoais.

        - Cria categorias padrão
        - Cria configurações de alerta padrão
        - Cria contas padrão

        Returns:
            Dict com resultados da inicialização.
        """
        results = {"categories": 0, "alert_configs": 0, "accounts": 0}

        # Categorias padrão
        results["categories"] = Categorizer.initialize_default_categories()

        # Configurações de alerta
        try:
            with db.session() as session:
                existing = session.query(AlertConfig).count()
                if existing == 0:
                    for cfg in DEFAULT_ALERT_CONFIGS:
                        alert_cfg = AlertConfig(**cfg)
                        session.add(alert_cfg)
                        results["alert_configs"] += 1
        except Exception as e:
            raise AgentError(f"Erro ao inicializar alertas: {e}")

        # Contas padrão
        try:
            with db.session() as session:
                existing = session.query(Account).count()
                if existing == 0:
                    for acc in DEFAULT_ACCOUNTS:
                        account = Account(**acc)
                        session.add(account)
                        results["accounts"] += 1
        except Exception as e:
            raise AgentError(f"Erro ao inicializar contas: {e}")

        return results

    # ── Transações ───────────────────────────────────────────────────

    def list_transactions(
        self,
        limit: int = 50,
        offset: int = 0,
        category_id: Optional[int] = None,
        account_id: Optional[int] = None,
        transaction_type: Optional[str] = None,
        days: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Lista transações com filtros opcionais."""
        try:
            with db.session() as session:
                query = session.query(Transaction).order_by(Transaction.date.desc())

                if category_id is not None:
                    query = query.filter(Transaction.category_id == category_id)
                if account_id is not None:
                    query = query.filter(Transaction.account_id == account_id)
                if transaction_type:
                    query = query.filter(Transaction.type == transaction_type)
                if days:
                    cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(days=days)
                    query = query.filter(Transaction.date >= cutoff)

                transactions = query.offset(offset).limit(limit).all()
                return [t.to_dict() for t in transactions]

        except DatabaseError as e:
            raise AgentError(f"Erro ao listar transações: {e}")

    def get_transaction(self, transaction_id: int) -> Optional[Dict[str, Any]]:
        """Busca uma transação específica pelo ID.

        Args:
            transaction_id: ID da transação.

        Returns:
            Dict com dados da transação ou None se não encontrada.
        """
        try:
            with db.session() as session:
                tx = session.query(Transaction).get(transaction_id)
                if not tx:
                    return None
                return tx.to_dict()
        except DatabaseError as e:
            raise AgentError(f"Erro ao buscar transação: {e}")

    def add_transaction(
        self,
        description: str,
        amount: float,
        date: Optional[str] = None,
        tx_type: str = "expense",
        category_name: Optional[str] = None,
        account_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Adiciona uma transação manualmente."""
        try:
            # Categoriza automaticamente se não for especificada
            category_id = None
            if category_name:
                with db.session() as session:
                    cat = session.query(Category).filter(
                        Category.name == category_name
                    ).first()
                    if cat:
                        category_id = cat.id
                        category_name = cat.name
            else:
                category_id, category_name = self.categorizer.categorize(description)

            # Parse date
            tx_date = datetime.now(timezone.utc)
            if date:
                for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"]:
                    try:
                        tx_date = datetime.strptime(date, fmt).replace(tzinfo=timezone.utc)
                        break
                    except ValueError:
                        continue

            transaction = Transaction(
                description=description[:500],
                amount=abs(amount),
                type=tx_type,
                category_id=category_id,
                category_name=category_name,
                account_id=account_id,
                date=tx_date,
                source="manual",
                notes=notes,
            )

            with db.session() as session:
                session.add(transaction)
                session.flush()
                result = transaction.to_dict()

            return result

        except (DatabaseError, Exception) as e:
            raise AgentError(f"Erro ao adicionar transação: {e}")

    def update_transaction(
        self,
        transaction_id: int,
        description: Optional[str] = None,
        amount: Optional[float] = None,
        tx_type: Optional[str] = None,
        category_name: Optional[str] = None,
        date: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Atualiza uma transação existente.

        Args:
            transaction_id: ID da transação.
            description: Nova descrição (opcional).
            amount: Novo valor (opcional).
            tx_type: Novo tipo - expense/income (opcional).
            category_name: Nome da nova categoria (opcional).
            date: Nova data no formato YYYY-MM-DD (opcional).
            notes: Novas observações (opcional).

        Returns:
            Dict com dados atualizados ou None se não encontrada.
        """
        try:
            with db.session() as session:
                tx = session.query(Transaction).get(transaction_id)
                if not tx:
                    return None

                if description is not None:
                    tx.description = description[:500]
                    # Re-categoriza se a descrição mudou e nenhuma categoria foi especificada
                    if category_name is None and tx.source == "manual":
                        cat_id, cat_name = self.categorizer.categorize(description)
                        tx.category_id = cat_id
                        tx.category_name = cat_name

                if amount is not None:
                    tx.amount = abs(amount)

                if tx_type is not None:
                    tx.type = tx_type

                if category_name is not None:
                    cat = session.query(Category).filter(
                        Category.name == category_name
                    ).first()
                    if cat:
                        tx.category_id = cat.id
                        tx.category_name = cat.name

                if date is not None:
                    tx_date = datetime.now(timezone.utc)
                    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"]:
                        try:
                            tx_date = datetime.strptime(date, fmt).replace(tzinfo=timezone.utc)
                            break
                        except ValueError:
                            continue
                    tx.date = tx_date

                if notes is not None:
                    tx.notes = notes

                session.add(tx)
                session.flush()
                return tx.to_dict()

        except DatabaseError as e:
            raise AgentError(f"Erro ao atualizar transação: {e}")
        except Exception as e:
            raise AgentError(f"Erro ao atualizar transação: {e}")

    def update_transaction_category(
        self, transaction_id: int, new_category_name: str
    ) -> bool:
        """
        Reclassifica uma transação e ensina o categorizador.

        Args:
            transaction_id: ID da transação.
            new_category_name: Nome da nova categoria.

        Returns:
            bool: True se sucesso.
        """
        return self.categorizer.learn_from_reclassification(
            transaction_id, new_category_name
        )

    def delete_transaction(self, transaction_id: int) -> bool:
        """Remove uma transação."""
        try:
            with db.session() as session:
                tx = session.query(Transaction).get(transaction_id)
                if not tx:
                    return False
                session.delete(tx)
            return True
        except Exception:
            return False

    # ── Importação ───────────────────────────────────────────────────

    def import_file(self, file_path: str) -> Dict[str, Any]:
        """
        Importa transações de um arquivo de extrato.

        Suporta: .csv, .xlsx, .xls, .pdf

        Args:
            file_path: Caminho do arquivo.

        Returns:
            Dict com resultado da importação.
        """
        file_lower = file_path.lower()
        result = {"imported": 0, "duplicates": 0, "errors": []}

        try:
            if file_lower.endswith(".csv"):
                importer = self.csv_importer
                source = "csv"
            elif file_lower.endswith((".xlsx", ".xls")):
                importer = self.excel_importer
                source = "excel"
            elif file_lower.endswith(".pdf"):
                importer = self.pdf_importer
                source = "pdf"
            else:
                return {
                    "imported": 0,
                    "duplicates": 0,
                    "errors": [f"Formato não suportado: {file_path}"],
                }

            imported, duplicates, errors = importer.import_file(file_path, source=source)
            return {
                "imported": imported,
                "duplicates": duplicates,
                "errors": errors,
            }

        except FinanceDataError as e:
            return {"imported": 0, "duplicates": 0, "errors": [str(e)]}
        except Exception as e:
            return {"imported": 0, "duplicates": 0, "errors": [f"Erro inesperado: {e}"]}

    # ── Dashboard / Resumo ───────────────────────────────────────────

    def get_dashboard(self, year: Optional[int] = None, month: Optional[int] = None) -> Dict[str, Any]:
        """
        Obtém o dashboard financeiro completo.

        Returns:
            Dict com: summary, balance_history, active_alerts, active_goals.
        """
        now = datetime.now(timezone.utc)
        year = year or now.year
        month = month or now.month

        summary = get_month_summary(year, month)
        balance_history = get_balance_history(days=90)

        # Busca alertas ativos
        active_alerts = []
        try:
            with db.session() as session:
                alerts = session.query(Alert).filter(
                    Alert.dismissed == 0,
                ).order_by(Alert.created_at.desc()).limit(20).all()
                active_alerts = [a.to_dict() for a in alerts]
        except Exception:
            pass

        # Busca metas ativas
        active_goals = []
        try:
            with db.session() as session:
                goals = session.query(FinancialGoal).filter(
                    FinancialGoal.status == "active",
                ).order_by(FinancialGoal.created_at.desc()).all()
                active_goals = [g.to_dict() for g in goals]
        except Exception:
            pass

        return {
            "summary": summary,
            "balance_history": balance_history,
            "active_alerts": active_alerts,
            "active_goals": active_goals,
        }

    def build_monthly_summary_prompt(
        self, year: int, month: int, summary: Optional[Dict[str, Any]] = None
    ) -> str:
        """Monta o prompt do resumo mensal (usado também pelo streaming do app desktop)."""
        return format_monthly_summary_prompt(month, year, summary or get_month_summary(year, month))

    def get_monthly_summary_ai(self, year: int, month: int) -> str:
        """
        Gera resumo em linguagem natural do mês usando IA.

        Args:
            year: Ano.
            month: Mês.

        Returns:
            str: Análise textual do mês.
        """
        summary = get_month_summary(year, month)
        if summary["transaction_count"] == 0:
            return "Nenhuma transação registrada neste período."

        prompt = self.build_monthly_summary_prompt(year, month, summary)

        if self.check_llm_available():
            try:
                return self.get_llm_analysis(prompt)
            except AgentError:
                pass

        # Fallback sem IA
        return (
            f"📊 Resumo de {month}/{year}:\n"
            f"  Receitas: R$ {summary['total_income']:.2f}\n"
            f"  Despesas: R$ {summary['total_expense']:.2f}\n"
            f"  Saldo: R$ {summary['balance']:.2f}\n"
            f"  Média diária: R$ {summary['avg_daily_expense']:.2f}\n"
            f"  Total de transações: {summary['transaction_count']}"
        )

    def get_multi_month_dashboard(self, months: int = 6) -> Dict[str, Any]:
        """
        Obtém dados agregados para gráficos do dashboard.

        Returns:
            Dict com: monthly_summaries, balance_history.
        """
        return {
            "monthly_summaries": get_multi_month_summary(months),
            "balance_history": get_balance_history(days=90),
        }

    # ── Metas Financeiras ────────────────────────────────────────────

    def create_goal(
        self,
        name: str,
        target_amount: float,
        deadline: Optional[str] = None,
        goal_type: str = "savings",
        priority: str = "medium",
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cria uma nova meta financeira."""
        deadline_dt = None
        if deadline:
            for fmt in ["%Y-%m-%d", "%d/%m/%Y"]:
                try:
                    deadline_dt = datetime.strptime(deadline, fmt).replace(tzinfo=None)
                    break
                except ValueError:
                    continue

        goal = FinancialGoal(
            name=name,
            description=description,
            target_amount=target_amount,
            goal_type=goal_type,
            priority=priority,
            deadline=deadline_dt,
        )

        try:
            with db.session() as session:
                session.add(goal)
                session.flush()
                result = goal.to_dict()
        except DatabaseError as e:
            raise AgentError(f"Erro ao criar meta: {e}")

        return result

    def list_goals(self, status: Optional[str] = "active") -> List[Dict[str, Any]]:
        """Lista metas financeiras."""
        try:
            with db.session() as session:
                query = session.query(FinancialGoal)
                if status:
                    query = query.filter(FinancialGoal.status == status)
                query = query.order_by(FinancialGoal.created_at.desc())
                return [g.to_dict() for g in query.all()]
        except DatabaseError as e:
            raise AgentError(f"Erro ao listar metas: {e}")

    def contribute_to_goal(self, goal_id: int, amount: float) -> Dict[str, Any]:
        """Adiciona valor a uma meta."""
        try:
            with db.session() as session:
                goal = session.query(FinancialGoal).get(goal_id)
                if not goal:
                    raise AgentError(f"Meta {goal_id} não encontrada.")
                if goal.status != "active":
                    raise AgentError(f"Meta '{goal.name}' não está ativa.")

                goal.current_amount += amount

                # Verifica se completou
                if goal.current_amount >= goal.target_amount:
                    goal.status = "completed"
                    goal.completed_at = datetime.now(timezone.utc)

                session.add(goal)
                session.flush()
                return goal.to_dict()
        except DatabaseError as e:
            raise AgentError(f"Erro ao contribuir para meta: {e}")

    def update_goal(
        self,
        goal_id: int,
        name: Optional[str] = None,
        target_amount: Optional[float] = None,
        deadline: Optional[str] = None,
        goal_type: Optional[str] = None,
        priority: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Atualiza uma meta financeira existente.

        Args:
            goal_id: ID da meta.
            name: Novo nome (opcional).
            target_amount: Novo valor alvo (opcional).
            deadline: Novo prazo YYYY-MM-DD (opcional).
            goal_type: Novo tipo (opcional).
            priority: Nova prioridade (opcional).
            description: Nova descrição (opcional).
            status: Novo status (opcional).

        Returns:
            Dict com dados atualizados ou None se não encontrada.
        """
        try:
            with db.session() as session:
                goal = session.query(FinancialGoal).get(goal_id)
                if not goal:
                    return None

                if name is not None:
                    goal.name = name.strip()
                if target_amount is not None:
                    goal.target_amount = target_amount
                if deadline is not None:
                    for fmt in ["%Y-%m-%d", "%d/%m/%Y"]:
                        try:
                            deadline_dt = datetime.strptime(deadline, fmt).replace(tzinfo=None)
                            goal.deadline = deadline_dt
                            break
                        except ValueError:
                            continue
                if goal_type is not None:
                    goal.goal_type = goal_type
                if priority is not None:
                    goal.priority = priority
                if description is not None:
                    goal.description = description
                if status is not None:
                    goal.status = status

                session.add(goal)
                session.flush()
                return goal.to_dict()
        except DatabaseError as e:
            raise AgentError(f"Erro ao atualizar meta: {e}")
        except Exception as e:
            raise AgentError(f"Erro ao atualizar meta: {e}")

    def delete_goal(self, goal_id: int) -> bool:
        """Remove uma meta financeira."""
        try:
            with db.session() as session:
                goal = session.query(FinancialGoal).get(goal_id)
                if not goal:
                    return False
                session.delete(goal)
            return True
        except Exception:
            return False

    def analyze_goal(self, goal_id: int) -> Dict[str, Any]:
        """
        Analisa uma meta com dados financeiros e IA.

        Returns:
            Dict com análise técnica + sugestão da IA.
        """
        try:
            with db.session() as session:
                goal = session.query(FinancialGoal).get(goal_id)
                if not goal:
                    raise AgentError(f"Meta {goal_id} não encontrada.")
                # Extrai dados dentro da sessão para evitar detached errors
                goal_data = goal.to_dict()
                goal_obj = goal  # Referência para salvar LLM suggestion depois
                goal_deadline = goal.deadline
        except DatabaseError as e:
            raise AgentError(f"Erro ao acessar meta: {e}")

        # Análise técnica
        analysis = get_goal_analysis(goal_data)

        # Sugestão da IA
        if self.check_llm_available():
            try:
                summary = get_month_summary(
                    datetime.now(timezone.utc).year,
                    datetime.now(timezone.utc).month,
                )
                avg_expense = summary["avg_daily_expense"]

                prompt = format_goal_prompt(
                    goal_name=goal_data["name"],
                    target=goal_data["target_amount"],
                    current=goal_data["current_amount"],
                    remaining=goal_data["remaining_amount"],
                    progress=goal_data["progress_percent"],
                    deadline=goal_deadline.strftime("%d/%m/%Y") if goal_deadline else "sem prazo",
                    days_left=goal_data["days_remaining"],
                    monthly_needed=analysis["monthly_needed"],
                    avg_daily_expense=avg_expense,
                    monthly_income=summary["total_income"],
                )

                ai_suggestion = self.get_llm_analysis(prompt)
                analysis["ai_suggestion"] = ai_suggestion

                # Salva sugestão no banco (nova sessão)
                if goal_obj:
                    try:
                        with db.session() as session:
                            g = session.query(FinancialGoal).get(goal_id)
                            if g:
                                g.ai_suggestion = json.dumps({"analysis": ai_suggestion})
                    except Exception:
                        pass

            except AgentError:
                analysis["ai_suggestion"] = "IA não disponível para análise detalhada."

        return analysis

    # ── Alertas ──────────────────────────────────────────────────────

    def check_alerts(self) -> List[Dict[str, Any]]:
        """Verifica e gera alertas automaticamente."""
        new_alerts = check_and_generate_alerts()
        saved = save_alerts(new_alerts)

        return [a.to_dict() for a in new_alerts[:saved]]

    def list_alerts(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Lista alertas."""
        try:
            with db.session() as session:
                query = session.query(Alert).order_by(Alert.created_at.desc())
                if active_only:
                    query = query.filter(Alert.dismissed == 0)
                return [a.to_dict() for a in query.limit(50).all()]
        except DatabaseError as e:
            raise AgentError(f"Erro ao listar alertas: {e}")

    def dismiss_alert(self, alert_id: int) -> bool:
        """Dispensa um alerta."""
        try:
            with db.session() as session:
                alert = session.query(Alert).get(alert_id)
                if not alert:
                    return False
                alert.dismissed = 1
                session.add(alert)
            return True
        except Exception:
            return False

    # ── Orçamento ──────────────────────────────────────────────────

    def get_budget_overview(
        self, year: Optional[int] = None, month: Optional[int] = None
    ) -> Dict[str, Any]:
        """Obtém visão de orçamento: limites vs realizado por categoria."""
        now = datetime.now(timezone.utc)
        return get_budget_overview(year or now.year, month or now.month)

    def set_category_budget(
        self, category_id: int, budget_limit: float
    ) -> Optional[Dict[str, Any]]:
        """
        Define o limite de orçamento para uma categoria.

        Args:
            category_id: ID da categoria.
            budget_limit: Limite em reais (será convertido para centavos).

        Returns:
            Dict da categoria atualizada ou None se não encontrada.
        """
        try:
            with db.session() as session:
                cat = session.query(Category).get(category_id)
                if not cat:
                    return None
                cat.budget_limit = int(budget_limit * 100)  # converte para centavos
                session.add(cat)
                session.flush()
                return cat.to_dict()
        except DatabaseError as e:
            raise AgentError(f"Erro ao definir orçamento: {e}")

    # ── Contas ──────────────────────────────────────────────────────

    def list_accounts(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Lista todas as contas financeiras."""
        try:
            with db.session() as session:
                query = session.query(Account).order_by(Account.created_at)
                if active_only:
                    query = query.filter(Account.is_active == 1)
                return [a.to_dict() for a in query.all()]
        except DatabaseError as e:
            raise AgentError(f"Erro ao listar contas: {e}")

    def get_account(self, account_id: int) -> Optional[Dict[str, Any]]:
        """Busca uma conta pelo ID."""
        try:
            with db.session() as session:
                acc = session.query(Account).get(account_id)
                return acc.to_dict() if acc else None
        except DatabaseError as e:
            raise AgentError(f"Erro ao buscar conta: {e}")

    def create_account(
        self,
        name: str,
        account_type: str = "checking",
        balance: float = 0.0,
        currency: str = "BRL",
        icon: str = "🏦",
        color: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cria uma nova conta financeira."""
        acc = Account(
            name=name.strip(),
            account_type=account_type,
            balance=balance,
            currency=currency,
            icon=icon,
            color=color,
            notes=notes,
        )
        try:
            with db.session() as session:
                session.add(acc)
                session.flush()
                return acc.to_dict()
        except DatabaseError as e:
            raise AgentError(f"Erro ao criar conta: {e}")

    def update_account(
        self,
        account_id: int,
        name: Optional[str] = None,
        account_type: Optional[str] = None,
        balance: Optional[float] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        notes: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        """Atualiza uma conta existente."""
        try:
            with db.session() as session:
                acc = session.query(Account).get(account_id)
                if not acc:
                    return None
                if name is not None:
                    acc.name = name.strip()
                if account_type is not None:
                    acc.account_type = account_type
                if balance is not None:
                    acc.balance = balance
                if icon is not None:
                    acc.icon = icon
                if color is not None:
                    acc.color = color
                if notes is not None:
                    acc.notes = notes
                if is_active is not None:
                    acc.is_active = 1 if is_active else 0
                session.add(acc)
                session.flush()
                return acc.to_dict()
        except DatabaseError as e:
            raise AgentError(f"Erro ao atualizar conta: {e}")

    def delete_account(self, account_id: int) -> bool:
        """Remove uma conta (desativa se tiver transacoes)."""
        try:
            with db.session() as session:
                acc = session.query(Account).get(account_id)
                if not acc:
                    return False
                tx_count = session.query(Transaction).filter(
                    Transaction.account_id == account_id
                ).count()
                if tx_count > 0:
                    acc.is_active = 0
                    session.add(acc)
                else:
                    session.delete(acc)
            return True
        except Exception:
            return False

    # ── Categorias ───────────────────────────────────────────────────

    def list_categories(self) -> List[Dict[str, Any]]:
        """Lista todas as categorias."""
        try:
            with db.session() as session:
                categories = session.query(Category).order_by(Category.sort_order).all()
                return [c.to_dict() for c in categories]
        except DatabaseError as e:
            raise AgentError(f"Erro ao listar categorias: {e}")

    def add_category(
        self,
        name: str,
        icon: str = "📦",
        keywords: Optional[List[str]] = None,
        budget_limit: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Adiciona uma nova categoria."""
        cat = Category(
            name=name,
            icon=icon,
            keywords=json.dumps(keywords or []),
            budget_limit=int(budget_limit * 100) if budget_limit else None,
        )
        try:
            with db.session() as session:
                session.add(cat)
            self.csv_importer.invalidate_cache()
            return cat.to_dict()
        except DatabaseError as e:
            raise AgentError(f"Erro ao criar categoria: {e}")
