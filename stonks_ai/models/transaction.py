"""Modelo de transações financeiras para controle de gastos pessoais."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from stonks_ai.database import Base


class Transaction(Base):
    """Transação financeira (receita ou despesa) do usuário."""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(String(500), nullable=False, index=True)
    amount = Column(Float, nullable=False)  # Positive = income, Negative = expense
    type = Column(String(20), nullable=False, default="expense")  # expense, income
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True, index=True)
    category_name = Column(String(100), nullable=True)  # Denormalizado para performance
    date = Column(DateTime, nullable=False, index=True)
    source = Column(String(20), nullable=False, default="manual")  # manual, csv, excel, pdf
    source_file = Column(String(500), nullable=True)
    is_recurring = Column(Integer, nullable=False, default=0)  # 0 = não, 1 = sim
    recurring_frequency = Column(String(20), nullable=True)  # monthly, yearly, weekly, biweekly
    recurrence_id = Column(String(64), nullable=True)  # Para agrupar recorrências
    notes = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # JSON list: ["essencial", "urgente"]
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationship
    category = relationship("Category", backref="transactions", lazy="select")

    def __repr__(self) -> str:
        return (
            f"<Transaction(desc='{self.description[:30]}', "
            f"amount={self.amount}, date={self.date})>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "amount": self.amount,
            "type": self.type,
            "category_id": self.category_id,
            "category_name": self.category_name or "Sem categoria",
            "date": self.date.isoformat() if self.date else None,
            "source": self.source,
            "is_recurring": bool(self.is_recurring),
            "recurring_frequency": self.recurring_frequency,
            "notes": self.notes,
            "tags": self.tags,
        }
