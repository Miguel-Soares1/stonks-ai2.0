"""Coletores de dados financeiros pessoais.

Módulo responsável por importar e categorizar transações financeiras
a partir de extratos bancários (CSV, Excel, PDF).
"""

from stonks_ai.collectors.finance.base import FinanceDataError, FinanceImporter

__all__ = ["FinanceDataError", "FinanceImporter"]
