"""Classe base para importadores de dados financeiros."""

import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from stonks_ai.collectors.finance import categorizer
from stonks_ai.database import db
from stonks_ai.models.transaction import Transaction


class FinanceDataError(Exception):
    """Erro relacionado a dados financeiros."""
    pass


class FinanceImporter(ABC):
    """Classe base abstrata para importadores de extratos financeiros."""

    def __init__(self):
        self._categorizer = categorizer.Categorizer()

    @abstractmethod
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parseia o arquivo de extrato e retorna lista de transações brutas.

        Returns:
            List[Dict] com chaves: description, amount, date, type
        """
        pass

    def import_file(self, file_path: str, source: str = "unknown") -> Tuple[int, int, List[str]]:
        """
        Pipeline completo: parse → validate → categorize → save.

        Args:
            file_path: Caminho do arquivo de extrato.
            source: Origem (csv, excel, pdf).

        Returns:
            Tuple (importadas, duplicatas, erros)
        """
        raw_transactions = self.parse(file_path)
        imported = 0
        duplicates = 0
        errors = []

        for raw in raw_transactions:
            try:
                # Valida dados mínimos
                if not raw.get("description") or not raw.get("amount"):
                    errors.append(f"Transação inválida: {raw}")
                    continue

                # Verifica duplicata
                if self._is_duplicate(raw):
                    duplicates += 1
                    continue

                # Categoriza
                category_id, category_name = self._categorize(raw["description"])

                # Cria transação
                amount = abs(raw["amount"])
                tx_type = raw.get("type") or ("income" if raw["amount"] > 0 else "expense")

                transaction = Transaction(
                    description=raw["description"][:500],
                    amount=amount,
                    type=tx_type,
                    category_id=category_id,
                    category_name=category_name,
                    date=self._parse_date(raw.get("date")),
                    source=source,
                    source_file=file_path,
                    notes=raw.get("notes"),
                )

                with db.session() as session:
                    session.add(transaction)

                imported += 1

            except Exception as e:
                errors.append(f"Erro ao importar '{raw.get('description', '?')}': {e}")

        return imported, duplicates, errors

    def _parse_date(self, date_val: Any) -> datetime:
        """Tenta converter valor para datetime."""
        if isinstance(date_val, datetime):
            return date_val
        if isinstance(date_val, str):
            # Tenta múltiplos formatos
            for fmt in [
                "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d",
                "%d-%m-%Y", "%m/%d/%Y", "%Y%m%d",
                "%d/%m/%y", "%Y-%m-%d %H:%M:%S",
            ]:
                try:
                    return datetime.strptime(date_val.strip(), fmt)
                except ValueError:
                    continue
        return datetime.now()

    def _is_duplicate(self, raw: Dict[str, Any]) -> bool:
        """Verifica se transação já foi importada (mesma descrição, valor e data)."""
        try:
            with db.session() as session:
                amount = abs(raw["amount"])
                tx_type = raw.get("type") or ("income" if raw["amount"] > 0 else "expense")
                date = self._parse_date(raw.get("date"))
                date_str = date.strftime("%Y-%m-%d")

                result = session.query(Transaction).filter(
                    Transaction.description == raw["description"][:500],
                    Transaction.amount == amount,
                    Transaction.type == tx_type,
                ).all()

                for tx in result:
                    if tx.date.strftime("%Y-%m-%d") == date_str:
                        return True
                return False
        except Exception:
            return False

    def _categorize(self, description: str) -> Tuple[Optional[int], str]:
        """
        Classifica uma transação com o mesmo categorizador das transações manuais
        (regras aprendidas + palavras-chave).

        Returns:
            Tuple (category_id, category_name)
        """
        return self._categorizer.categorize(description)

    def invalidate_cache(self):
        """Invalida cache de categorias (após adicionar nova categoria)."""
        categorizer.invalidate_cache()
