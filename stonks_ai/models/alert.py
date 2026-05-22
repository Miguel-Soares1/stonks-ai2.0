"""Modelos de alertas e configurações de alertas financeiros."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text

from stonks_ai.database import Base


class Alert(Base):
    """Alerta inteligente sobre padrões financeiros."""

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_type = Column(String(50), nullable=False, index=True)
    # spending_pattern, balance_low, budget_exceeded, subscription_change,
    # goal_at_risk, unusual_transaction, bill_reminder
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, default="info")  # info, warning, critical
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    related_transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    related_goal_id = Column(Integer, ForeignKey("financial_goals.id"), nullable=True)
    data = Column(Text, nullable=True)  # JSON com dados contextuais
    read = Column(Integer, nullable=False, default=0)  # 0 = não lido, 1 = lido
    dismissed = Column(Integer, nullable=False, default=0)  # 0 = ativo, 1 = dispensado
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self) -> str:
        return f"<Alert(type='{self.alert_type}', severity='{self.severity}', title='{self.title[:30]}')>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "alert_type": self.alert_type,
            "title": self.title,
            "message": self.message,
            "severity": self.severity,
            "read": bool(self.read),
            "dismissed": bool(self.dismissed),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AlertConfig(Base):
    """Configuração de alertas financeiros."""

    __tablename__ = "alert_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_type = Column(String(50), nullable=False, unique=True, index=True)
    enabled = Column(Integer, nullable=False, default=1)  # 0 = disabled, 1 = enabled
    threshold = Column(Float, nullable=True)  # Threshold percentual (ex: 20% de aumento)
    min_interval_hours = Column(Integer, nullable=False, default=24)  # Evitar repetição
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self) -> str:
        return f"<AlertConfig(type='{self.alert_type}', enabled={bool(self.enabled)})>"


DEFAULT_ALERT_CONFIGS = [
    {"alert_type": "spending_pattern", "enabled": 1, "threshold": 20.0, "min_interval_hours": 48},
    {"alert_type": "balance_low", "enabled": 1, "threshold": None, "min_interval_hours": 24},
    {"alert_type": "budget_exceeded", "enabled": 1, "threshold": 10.0, "min_interval_hours": 72},
    {"alert_type": "subscription_change", "enabled": 1, "threshold": 5.0, "min_interval_hours": 168},
    {"alert_type": "goal_at_risk", "enabled": 1, "threshold": 10.0, "min_interval_hours": 72},
    {"alert_type": "unusual_transaction", "enabled": 1, "threshold": None, "min_interval_hours": 24},
    {"alert_type": "bill_reminder", "enabled": 0, "threshold": None, "min_interval_hours": 24},
]
