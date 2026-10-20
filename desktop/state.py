"""
Instâncias compartilhadas dos agentes.

São criadas sob demanda e recriadas quando os ajustes de IA mudam
(provider/modelo), para que o novo cliente LLM passe a valer.
"""

from typing import Optional

from stonks_ai.agents.financial_agent import FinancialAgent
from stonks_ai.agents.personal_finance_agent import PersonalFinanceAgent

_financial: Optional[FinancialAgent] = None
_personal: Optional[PersonalFinanceAgent] = None


def financial_agent() -> FinancialAgent:
    global _financial
    if _financial is None:
        _financial = FinancialAgent()
    return _financial


def personal_agent() -> PersonalFinanceAgent:
    global _personal
    if _personal is None:
        _personal = PersonalFinanceAgent()
    return _personal


def reset_agents() -> None:
    global _financial, _personal
    _financial = None
    _personal = None
