"""Importador de extratos financeiros em formato Excel (.xlsx/.xls).

Suporta múltiplas sheets e detecta automaticamente colunas relevantes.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from stonks_ai.collectors.finance.base import FinanceDataError, FinanceImporter


class ExcelImporter(FinanceImporter):
    """Importa transações de arquivos Excel de extratos bancários."""

    def __init__(self):
        super().__init__()
        self._sheet_name: Optional[str] = None

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """Parseia arquivo Excel e retorna lista de transações."""
        path = Path(file_path)
        if not path.exists():
            raise FinanceDataError(f"Arquivo não encontrado: {file_path}")
        if path.suffix.lower() not in (".xlsx", ".xls"):
            raise FinanceDataError(f"Formato não suportado: {path.suffix}")

        transactions = []

        try:
            # Lê todas as sheets do Excel
            xls = pd.ExcelFile(file_path)

            for sheet_name in xls.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
                transactions.extend(self._parse_dataframe(df, sheet_name))

        except Exception as e:
            raise FinanceDataError(f"Erro ao ler Excel: {e}")

        return transactions

    def _parse_dataframe(self, df: pd.DataFrame, sheet_name: str) -> List[Dict[str, Any]]:
        """Parseia um DataFrame do pandas em transações."""
        transactions = []

        # Detecta linha de cabeçalho
        header_row = self._find_header_row(df)
        if header_row is not None:
            df.columns = df.iloc[header_row]
            df = df.iloc[header_row + 1:].reset_index(drop=True)

        # Detecta colunas relevantes
        col_map = self._detect_columns(df)

        if not col_map.get("description") or not col_map.get("amount"):
            return []

        for idx, row in df.iterrows():
            try:
                desc = str(row[col_map["description"]])
                amount_raw = row[col_map["amount"]]

                if pd.isna(amount_raw):
                    continue

                amount = float(amount_raw)
                if amount == 0:
                    continue

                # Data
                date_val = None
                if col_map.get("date"):
                    date_val = row[col_map["date"]]
                    if pd.isna(date_val):
                        date_val = None

                # Tipo
                tx_type = "expense"
                if amount > 0:
                    tx_type = "income"
                else:
                    amount = abs(amount)

                transactions.append({
                    "description": desc[:500],
                    "amount": amount,
                    "date": date_val,
                    "type": tx_type,
                    "notes": None,
                })

            except (ValueError, TypeError, KeyError):
                continue

        return transactions

    def _find_header_row(self, df: pd.DataFrame) -> Optional[int]:
        """Encontra a linha que contém o cabeçalho (data, descrição, valor)."""
        keywords = ["data", "descrição", "descricao", "valor", "lançamento",
                     "historico", "date", "description", "amount", "value"]

        for idx in range(min(10, len(df))):
            row_str = " ".join(str(v).lower() for v in df.iloc[idx].values)
            matches = sum(1 for kw in keywords if kw in row_str)
            if matches >= 2:
                return idx
        return 0  # Assume primeira linha

    def _detect_columns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detecta quais colunas são data, descrição e valor."""
        col_map = {"description": None, "amount": None, "date": None}

        for col in df.columns:
            col_str = str(col).lower().strip()

            # Descrição
            if any(kw in col_str for kw in ["descrição", "descricao", "historico",
                                             "desc", "description", "lançamento"]):
                col_map["description"] = col

            # Valor
            elif any(kw in col_str for kw in ["valor", "amount", "value", "preço",
                                                "preco", "total", "saldo"]):
                col_map["amount"] = col

            # Data
            elif any(kw in col_str for kw in ["data", "date", "dt", "vencimento"]):
                col_map["date"] = col

        # Fallback: se não achou, tenta pela posição
        if col_map["description"] is None and len(df.columns) > 0:
            col_map["description"] = df.columns[0]
        if col_map["amount"] is None and len(df.columns) > 2:
            col_map["amount"] = df.columns[2]
        if col_map["date"] is None and len(df.columns) > 1:
            col_map["date"] = df.columns[1]

        return col_map
