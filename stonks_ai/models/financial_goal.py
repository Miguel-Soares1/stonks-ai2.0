"""Modelo de metas financeiras."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from stonks_ai.database import Base


def _utcnow() -> datetime:
    """Retorna datetime UTC naive (sem timezone) para compatibilidade com SQLite."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class FinancialGoal(Base):
    """Meta financeira do usuário com acompanhamento de progresso."""

    __tablename__ = "financial_goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    target_amount = Column(Float, nullable=False)  # Valor alvo
    current_amount = Column(Float, nullable=False, default=0.0)  # Valor atual acumulado
    deadline = Column(DateTime, nullable=True)  # Prazo opcional
    goal_type = Column(String(30), nullable=False, default="savings")  # savings, debt, purchase, emergency
    priority = Column(String(10), nullable=False, default="medium")  # low, medium, high
    status = Column(String(20), nullable=False, default="active")  # active, completed, cancelled, paused
    monthly_contribution = Column(Float, nullable=True)  # Contribuição mensal sugerida/real
    ai_suggestion = Column(Text, nullable=True)  # JSON com sugestão da IA
    icon = Column(String(10), nullable=False, default="🎯")
    color = Column(String(7), nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow,
                        onupdate=_utcnow, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<FinancialGoal(name='{self.name}', "
            f"{self.current_amount:.0f}/{self.target_amount:.0f}, "
            f"status='{self.status}')>"
        )

    @property
    def progress_percent(self) -> float:
        """Progresso da meta em porcentagem (0-100)."""
        if self.target_amount <= 0:
            return 0.0
        return min(100.0, round((self.current_amount / self.target_amount) * 100, 1))

    @property
    def remaining_amount(self) -> float:
        """Valor restante para atingir a meta."""
        return max(0.0, self.target_amount - self.current_amount)

    @property
    def days_remaining(self) -> int:
        """Dias restantes até o prazo (0 se sem prazo ou vencido)."""
        if not self.deadline:
            return 0
        delta = self.deadline - _utcnow()
        return max(0, delta.days)

    @property
    def is_on_track(self) -> bool:
        """Verifica se o progresso está dentro do esperado para o prazo."""
        if not self.deadline or self.days_remaining <= 0:
            return True
        total_days = (self.deadline - self.created_at).days
        if total_days <= 0:
            return True
        elapsed_days = (_utcnow() - self.created_at).days
        expected_progress = min(100.0, (elapsed_days / total_days) * 100)
        return self.progress_percent >= expected_progress

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "target_amount": self.target_amount,
            "current_amount": self.current_amount,
            "progress_percent": self.progress_percent,
            "remaining_amount": self.remaining_amount,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "days_remaining": self.days_remaining,
            "is_on_track": self.is_on_track,
            "goal_type": self.goal_type,
            "priority": self.priority,
            "status": self.status,
            "monthly_contribution": self.monthly_contribution,
            "icon": self.icon,
            "color": self.color,
        }
