"""Importador de extratos financeiros em formato CSV.

Suporta formatos de: Nubank, Itaú, Bradesco, Santander, Inter, C6 Bank
e formatos genéricos com mapeamento configurável de colunas.
"""

import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from stonks_ai.collectors.finance.base import FinanceDataError, FinanceImporter


# Padrões de colunas por banco (descrição, valor, data, tipo)
BANK_CSV_PATTERNS = {
    "nubank": {
        "date_col": 0,
        "description_col": 1,
        "amount_col": 2,
        "has_header": True,
        "delimiter": ",",
        "encoding": "utf-8",
        "date_format": "%Y-%m-%d",
    },
    "inter": {
        "date_col": 0,
        "description_col": 1,
        "amount_col": 2,
        "has_header": True,
        "delimiter": ";",
        "encoding": "utf-8",
        "date_format": "%d/%m/%Y",
    },
    "c6": {
        "date_col": 0,
        "description_col": 2,
        "amount_col": 1,
        "has_header": True,
        "delimiter": ",",
        "encoding": "utf-8",
        "date_format": "%Y-%m-%d",
    },
}


def detect_bank_from_filename(file_path: str) -> Optional[str]:
    """Detecta o banco pelo nome do arquivo."""
    name = Path(file_path).name.lower()
    for bank in ["nubank", "inter", "c6", "itau", "bradesco", "santander"]:
        if bank in name:
            return bank
    return None


def detect_bank_from_content(headers: List[str]) -> Optional[str]:
    """Detecta o banco pelos cabeçalhos do CSV."""
    header_str = " ".join(h.lower() for h in headers)
    patterns = {
        "nubank": ["data", "descrição", "valor"],
        "inter": ["data", "lançamento", "valor"],
        "c6": ["data", "valor", "descrição"],
        "itau": ["data", "historico", "valor"],
    }
    for bank, required in patterns.items():
        if all(p in header_str for p in required):
            return bank
    return None


class CSVImporter(FinanceImporter):
    """Importa transações de arquivos CSV de extratos bancários."""

    def __init__(self):
        super().__init__()
        self._column_map: Optional[Dict[str, int]] = None

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """Parseia arquivo CSV e retorna lista de transações."""
        path = Path(file_path)
        if not path.exists():
            raise FinanceDataError(f"Arquivo não encontrado: {file_path}")
        if path.suffix.lower() not in (".csv", ".txt"):
            raise FinanceDataError(f"Formato não suportado: {path.suffix}")

        bank = detect_bank_from_filename(file_path)
        pattern = BANK_CSV_PATTERNS.get(bank, {}) if bank else {}

        transactions = []
        encoding = pattern.get("encoding", "utf-8")
        delimiter = pattern.get("delimiter", ",")
        has_header = pattern.get("has_header", True)
        start_row = 0  # Inicializado antes do try para evitar NameError no handler

        try:
            with open(file_path, "r", encoding=encoding) as f:
                sample = f.read(4096)
                f.seek(0)

                # Detecta delimitador automaticamente
                if not delimiter or delimiter == ",":
                    sniffer = csv.Sniffer()
                    try:
                        dialect = sniffer.sniff(sample)
                        delimiter = dialect.delimiter
                    except csv.Error:
                        delimiter = ","  # fallback

                reader = csv.reader(f, delimiter=delimiter)
                rows = list(reader)

            if not rows:
                return []

            # Detecta banco pelo conteúdo se não foi pelo nome
            if not bank:
                bank = detect_bank_from_content(rows[0])

            if has_header or bank:
                # Pula linhas de cabeçalho
                for i, row in enumerate(rows):
                    row_str = " ".join(row).lower()
                    if any(kw in row_str for kw in [
                        "data", "descrição", "valor", "lançamento",
                        "historico", "date", "description", "amount",
                    ]):
                        start_row = i + 1
                        break

            # Processa linhas
            for row in rows[start_row:]:
                if not row or all(not cell.strip() for cell in row):
                    continue

                tx = self._parse_row(row, pattern, bank)
                if tx:
                    transactions.append(tx)

        except UnicodeDecodeError:
            # Tenta encoding alternativo
            try:
                with open(file_path, "r", encoding="latin-1") as f:
                    reader = csv.reader(f, delimiter=delimiter)
                    rows = list(reader)

                for row in rows[start_row:]:
                    if not row or all(not cell.strip() for cell in row):
                        continue
                    tx = self._parse_row(row, pattern, bank)
                    if tx:
                        transactions.append(tx)
            except Exception as e:
                raise FinanceDataError(f"Erro ao ler CSV (latin-1): {e}")
        except Exception as e:
            raise FinanceDataError(f"Erro ao ler CSV: {e}")

        return transactions

    def _parse_row(
        self,
        row: List[str],
        pattern: dict,
        bank: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Parseia uma linha do CSV em uma transação."""
        try:
            cells = [c.strip() for c in row]

            if pattern:
                # Usa padrão conhecido do banco
                date_str = cells[pattern["date_col"]]
                desc = cells[pattern["description_col"]]
                amount_str = cells[pattern["amount_col"]]
            else:
                # Tenta detectar colunas automaticamente
                desc = ""
                amount_str = ""
                date_str = ""

                for cell in cells:
                    if re.match(r"^[\d,.]+$", cell.replace(".", "").replace(",", "")):
                        amount_str = cell
                    elif re.match(r"\d{2}/\d{2}/\d{4}", cell) or re.match(r"\d{4}-\d{2}-\d{2}", cell):
                        date_str = cell
                    elif len(cell) > 5 and not desc:
                        desc = cell

            if not desc or not amount_str:
                return None

            # Normaliza valor (lida com , e .)
            amount = self._parse_amount(amount_str)
            if amount == 0:
                return None

            # Detecta tipo pelo sinal
            tx_type = "expense"
            if amount > 0:
                tx_type = "income"
            else:
                amount = abs(amount)

            return {
                "description": desc[:500],
                "amount": amount,
                "date": date_str,
                "type": tx_type,
            }

        except (IndexError, ValueError, TypeError):
            return None

    def _parse_amount(self, amount_str: str) -> float:
        """Normaliza string de valor para float."""
        amount_str = amount_str.strip()
        # Remove símbolos de moeda
        amount_str = re.sub(r'[R$\s]', '', amount_str)
        # Lida com formato brasileiro (1.234,56) e americano (1,234.56)
        if "," in amount_str and "." in amount_str:
            # Formato brasileiro: 1.234,56
            if amount_str.rfind(",") > amount_str.rfind("."):
                amount_str = amount_str.replace(".", "").replace(",", ".")
            # Formato americano: 1,234.56
            else:
                amount_str = amount_str.replace(",", "")
        elif "," in amount_str and "." not in amount_str:
            amount_str = amount_str.replace(",", ".")

        try:
            value = float(amount_str)
            return value
        except ValueError:
            return 0.0
