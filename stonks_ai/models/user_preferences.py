"""Modelo de preferências do usuário."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from stonks_ai.database import Base


class UserPreference(Base):
    """Preferência genérica do usuário (chave-valor)."""

    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), nullable=False, unique=True, index=True)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self) -> str:
        return f"<UserPreference(key='{self.key}', value='{self.value[:50]}...')>"
