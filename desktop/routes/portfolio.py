"""Rotas da carteira de investimentos: posições, operações e importação dos extratos da B3."""

import re
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from stonks_ai.collectors.finance import b3_importer
from stonks_ai.collectors.finance.base import FinanceDataError
from stonks_ai.utils import portfolio

router = APIRouter(prefix="/api/portfolio")

Kind = Literal["buy", "sell", "dividend", "jcp", "income", "bonus", "grouping"]
MAX_IMPORT_BYTES = 20 * 1024 * 1024


class OperationIn(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    kind: Kind
    date: date
    quantity: float = Field(default=0, ge=0)
    price: float = Field(default=0, ge=0)
    fees: float = Field(default=0, ge=0)
    amount: float = Field(default=0, ge=0)
    notes: Optional[str] = Field(default=None, max_length=500)


@router.get("")
def overview() -> Dict[str, Any]:
    """Posições com cotação, totais e proventos dos últimos 12 meses."""
    return portfolio.overview()


@router.get("/operations")
def operations(ticker: Optional[str] = None) -> List[Dict[str, Any]]:
    return [op.to_dict() for op in portfolio.list_operations(ticker)]


@router.post("/operations", status_code=201)
def add_operation(body: OperationIn) -> Dict[str, Any]:
    try:
        op = portfolio.add_operation(
            body.ticker, body.kind, body.date, quantity=body.quantity, price=body.price,
            fees=body.fees, amount=body.amount, notes=(body.notes or "").strip() or None,
        )
    except portfolio.PortfolioError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return op.to_dict()


@router.delete("/operations/{op_id}", status_code=204)
def delete_operation(op_id: int) -> None:
    if not portfolio.delete_operation(op_id):
        raise HTTPException(status_code=404, detail="Operação não encontrada.")


@router.post("/import")
async def import_b3(request: Request, filename: str) -> Dict[str, Any]:
    """Importa um extrato da B3 (Negociação ou Movimentação). O corpo é o próprio arquivo."""
    suffix = Path(filename).suffix.lower()
    if suffix not in b3_importer.SUFFIXES:
        raise HTTPException(status_code=422, detail="Formato não suportado. Baixe o extrato da B3 em Excel (.xlsx).")
    content = await request.body()
    if not content:
        raise HTTPException(status_code=422, detail="O arquivo está vazio.")
    if len(content) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo maior que 20 MB.")

    safe_name = re.sub(r"[^\w.\- ]", "_", Path(filename).name)[:120]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / safe_name
        path.write_bytes(content)
        try:
            parsed = b3_importer.parse(str(path))
        except FinanceDataError as e:
            raise HTTPException(status_code=422, detail=str(e))
    imported, duplicates = portfolio.save_imported(parsed["rows"])
    return {
        "file_type": parsed["file_type"],
        "imported": imported,
        "duplicates": duplicates,
        "skipped": parsed["skipped"],
        "tickers": sorted({r["ticker"] for r in parsed["rows"]}),
    }
