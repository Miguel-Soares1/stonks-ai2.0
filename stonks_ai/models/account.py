"""Modelo de contas financeiras para controle multi-conta."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from stonks_ai.database import Base


def _utcnow() -> datetime:
    """Retorna datetime UTC naive (sem timezone) para compatibilidade com SQLite."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Account(Base):
    """Conta financeira do usuário (corrente, poupança, cartão, etc.)."""

    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    account_type = Column(
        String(30), nullable=False, default="checking", index=True
    )  # checking, savings, credit_card, investment, cash, other
    balance = Column(Float, nullable=False, default=0.0)
    currency = Column(String(10), nullable=False, default="BRL")
    icon = Column(String(10), nullable=False, default="🏦")
    color = Column(String(7), nullable=True)  # Hex color
    notes = Column(Text, nullable=True)
    is_active = Column(Integer, nullable=False, default=1)  # 0=inactive, 1=active
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Account(name='{self.name}', type='{self.account_type}', balance={self.balance})>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "account_type": self.account_type,
            "balance": self.balance,
            "currency": self.currency,
            "icon": self.icon,
            "color": self.color,
            "notes": self.notes,
            "is_active": bool(self.is_active),
        }


# Contas padrão para inicialização
DEFAULT_ACCOUNTS = [
    {
        "name": "Conta Corrente",
        "account_type": "checking",
        "icon": "🏦",
        "color": "#06D6A0",
        "currency": "BRL",
        "balance": 0.0,
    },
    {
        "name": "Cartão de Crédito",
        "account_type": "credit_card",
        "icon": "💳",
        "color": "#FF006E",
        "currency": "BRL",
        "balance": 0.0,
    },
]
