"""Modelo das operações da carteira de investimentos (compras, vendas, proventos e eventos)."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from stonks_ai.database import Base

# Tipos de operação. As posições são sempre recalculadas a partir delas (stonks_ai/utils/portfolio.py).
OPERATION_KINDS = {
    "buy": "Compra",
    "sell": "Venda",
    "dividend": "Dividendo",
    "jcp": "Juros sobre capital próprio",
    "income": "Rendimento",
    "bonus": "Desdobramento ou bonificação",
    "grouping": "Grupamento",
}
INCOME_KINDS = {"dividend", "jcp", "income"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class InvestmentOperation(Base):
    """Uma linha do histórico da carteira.

    - buy/sell: quantity e price por cota; fees somam ao custo da compra e saem do valor da venda.
    - dividend/jcp/income: amount é o valor recebido (líquido, como a B3 informa).
    - bonus: cotas recebidas em desdobramento (price 0) ou bonificação (price = custo atribuído).
    - grouping: cotas que deixaram de existir num grupamento; o custo total não muda.
    """

    __tablename__ = "investment_operations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False, index=True)
    kind = Column(String(20), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    quantity = Column(Float, nullable=False, default=0.0)
    price = Column(Float, nullable=False, default=0.0)
    fees = Column(Float, nullable=False, default=0.0)
    amount = Column(Float, nullable=False, default=0.0)
    source = Column(String(20), nullable=False, default="manual")  # manual, b3
    # Identifica a linha do extrato da B3: importar o mesmo arquivo de novo não duplica nada
    import_key = Column(String(64), nullable=True, unique=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<InvestmentOperation({self.kind} {self.ticker} qty={self.quantity} date={self.date})>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ticker": self.ticker,
            "kind": self.kind,
            "kind_label": OPERATION_KINDS.get(self.kind, self.kind),
            "date": self.date.date().isoformat() if self.date else None,
            "quantity": self.quantity,
            "price": self.price,
            "fees": self.fees,
            "amount": self.amount,
            "source": self.source,
            "notes": self.notes,
        }
