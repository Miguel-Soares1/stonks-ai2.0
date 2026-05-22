"""Importador de extratos financeiros em formato PDF.

Usa parsing de texto via PyMuPDF (fitz) ou pdfplumber para extrair
dados estruturados de extratos bancários em PDF.

Requer: pip install pymupdf pdfplumber
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from stonks_ai.collectors.finance.base import FinanceDataError, FinanceImporter

logger = logging.getLogger(__name__)


class PDFImporter(FinanceImporter):
    """Importa transações de arquivos PDF de extratos bancários."""

    def __init__(self):
        super().__init__()
        self._text_cache: Optional[str] = None

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """Parseia arquivo PDF e retorna lista de transações."""
        path = Path(file_path)
        if not path.exists():
            raise FinanceDataError(f"Arquivo não encontrado: {file_path}")
        if path.suffix.lower() != ".pdf":
            raise FinanceDataError(f"Formato não suportado: {path.suffix}")

        # Extrai texto do PDF
        text = self._extract_text(file_path)
        if not text.strip():
            raise FinanceDataError("Não foi possível extrair texto do PDF")

        # Tenta parsing estruturado
        transactions = self._parse_structured(text)

        # Se não encontrou transações, tenta com IA
        if not transactions:
            transactions = self._parse_with_llm(text)

        return transactions

    def _extract_text(self, file_path: str) -> str:
        """Extrai texto de um arquivo PDF usando bibliotecas disponíveis."""
        text = ""

        # Tenta pymupdf (mais rápido)
        try:
            import fitz
            doc = fitz.open(file_path)
            for page in doc:
                text += page.get_text()
            doc.close()
            if text.strip():
                return text
        except ImportError:
            logger.debug("PyMuPDF (fitz) não disponível. Pulando...")
        except Exception as e:
            logger.warning("Erro ao processar PDF com PyMuPDF: %s", e)

        # Tenta pdfplumber (mais preciso para tabelas)
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            if text.strip():
                return text
        except ImportError:
            logger.debug("pdfplumber não disponível. Pulando...")
        except Exception as e:
            logger.warning("Erro ao processar PDF com pdfplumber: %s", e)

        if not text.strip():
            raise FinanceDataError(
                "Não foi possível extrair texto do PDF. "
                "Instale: pip install pymupdf pdfplumber"
            )

        return text

    def _parse_structured(self, text: str) -> List[Dict[str, Any]]:
        """
        Tenta extrair transações de forma estruturada usando regex.

        Busca padrões como:
        - 01/01/2024 DESCRICAO 123,45
        - 2024-01-01 Descrição R$ 123.45
        """
        transactions = []
        lines = text.split("\n")

        # Padrão: data + descrição + valor
        date_patterns = [
            r"(\d{2}/\d{2}/\d{4})",  # 01/01/2024
            r"(\d{2}/\d{2}/\d{2})",   # 01/01/24
            r"(\d{4}-\d{2}-\d{2})",   # 2024-01-01
        ]

        amount_patterns = [
            r"([\d,.]+)$",                      # 123,45 no fim da linha
            r"R?\$\s*([\d,.]+)",                 # R$ 123,45
            r"([\d,.]+)\s*$",                    # 123.45 no fim
            r"([\d,.]+)\s*[CD]",                 # 123,45 C / 123,45 D
        ]

        desc_keywords = re.compile(
            r"(PAGAMENTO|TRANSFERENCIA|TED|DOC|PIX|DEBITO|CREDITO|"
            r"TARIFA|IOF|JUROS|MULTA|ALUGUEL|CONTA|FATURA|"
            r"IFOOD|UBER|NETFLIX|SPOTIFY)", re.IGNORECASE
        )

        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue

            # Pula cabeçalhos
            if any(kw in line.lower() for kw in ["extrato", "banco", "agência",
                                                   "conta", "saldo", "página",
                                                   "data", "descrição", "valor",
                                                   "lançamento", "documento"]):
                continue

            date_found = None
            for dp in date_patterns:
                m = re.search(dp, line)
                if m:
                    date_found = m.group(1)
                    break

            if not date_found:
                continue

            # Extrai valor
            amount_found = None
            for ap in amount_patterns:
                m = re.search(ap, line)
                if m:
                    try:
                        val = m.group(1).strip()
                        # Normaliza valor com formatação brasileira (1.234,56) ou americana (1,234.56)
                        if "," in val and "." in val:
                            # Formato brasileiro: 1.234,56
                            if val.rfind(",") > val.rfind("."):
                                val = val.replace(".", "").replace(",", ".")
                            # Formato americano: 1,234.56
                            else:
                                val = val.replace(",", "")
                        elif "," in val:
                            val = val.replace(",", ".")
                        val = val.replace(" ", "")
                        amount_found = float(val)
                        break
                    except ValueError:
                        continue

            if amount_found is None or amount_found == 0:
                continue

            # Extrai descrição (remove data e valor)
            desc = line
            for dp in date_patterns:
                desc = re.sub(dp, "", desc)
            for ap in amount_patterns:
                desc = re.sub(ap, "", desc)
            # Remove R$ currency prefix
            desc = re.sub(r"\bR?\$\s*", "", desc)
            # Remove trailing standalone C (crédito) or D (débito) marker
            desc = re.sub(r"\s*[CD]\s*$", "", desc)
            desc = desc.strip()

            if not desc or len(desc) < 3:
                continue

            # Detecta tipo (C = crédito, D = débito)
            tx_type = "expense"
            # Verifica se a linha termina com C (crédito) ou D (débito) isolado
            if re.search(r"\bC\s*$", line):
                tx_type = "income"
            elif re.search(r"\bD\s*$", line):
                tx_type = "expense"
            if "CRÉDITO" in desc.upper() or "CREDITO" in desc.upper():
                tx_type = "income"
            if "DÉBITO" in desc.upper() or "DEBITO" in desc.upper():
                tx_type = "expense"

            transactions.append({
                "description": desc[:500],
                "amount": amount_found,
                "date": date_found,
                "type": tx_type,
            })

        return transactions

    def _parse_with_llm(self, text: str) -> List[Dict[str, Any]]:
        """
        Usa IA (Ollama) para extrair transações de texto não estruturado.
        Fallback quando regex não consegue extrair.
        """
        try:
            from stonks_ai.llm.client import OllamaClient

            llm = OllamaClient()
            if not llm.is_available():
                return []

            prompt = (
                "Extraia todas as transações financeiras do texto abaixo. "
                "Para cada transação, retorne: descrição, valor (apenas número), "
                "data, e tipo (expense/income).\n\n"
                "Responda APENAS com JSON puro, sem formatação adicional, "
                "no formato:\n"
                '[{"description": "...", "amount": 123.45, "date": "2024-01-01", "type": "expense"}]\n\n'
                f"Texto do extrato:\n{text[:3000]}"
            )

            response = llm.generate_structured(prompt)
            transactions = json.loads(response)

            if isinstance(transactions, list):
                # Valida cada transação
                valid = []
                for tx in transactions:
                    if tx.get("description") and tx.get("amount"):
                        valid.append({
                            "description": str(tx["description"])[:500],
                            "amount": abs(float(tx["amount"])),
                            "date": tx.get("date", ""),
                            "type": tx.get("type", "expense"),
                        })
                return valid

        except Exception as e:
            logger.warning("Erro no parsing via LLM: %s", e)

        return []
