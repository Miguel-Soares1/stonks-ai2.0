"""Rotas de exportação: planilhas gravadas na pasta Downloads e abertas no Explorer."""

import subprocess
import sys
from datetime import date
from typing import Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from stonks_ai import reports

router = APIRouter(prefix="/api/export")


class YearIn(BaseModel):
    year: int = Field(ge=2000, le=2100)


class FileIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


def _saved(path) -> Dict[str, str]:
    return {"name": path.name, "folder": str(path.parent), "path": str(path)}


@router.post("/transactions")
def export_transactions(body: YearIn) -> Dict[str, str]:
    """Transações do ano, resumo por mês e despesas por categoria."""
    if body.year > date.today().year:
        raise HTTPException(status_code=422, detail="Escolha um ano que já começou.")
    return _saved(reports.save(reports.transactions_workbook(body.year), f"stonks-transacoes-{body.year}.xlsx"))


@router.post("/ir")
def export_ir(body: YearIn) -> Dict[str, str]:
    """Carteira para o Imposto de Renda: bens e direitos, proventos e vendas do ano."""
    if body.year > date.today().year:
        raise HTTPException(status_code=422, detail="Escolha um ano que já começou.")
    return _saved(reports.save(reports.ir_workbook(body.year), f"stonks-carteira-ir-{body.year}.xlsx"))


@router.post("/show", status_code=204)
def show_in_folder(body: FileIn) -> None:
    """Abre o Explorer com o arquivo exportado selecionado.

    Só aceita um nome de arquivo dentro da pasta de exportação: a rota não abre caminhos quaisquer.
    """
    folder = reports.export_dir().resolve()
    path = (folder / body.name).resolve()
    if path.parent != folder or path.suffix.lower() != ".xlsx" or not path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado na pasta de exportação.")
    if sys.platform != "win32":
        raise HTTPException(status_code=501, detail="Disponível só no Windows.")
    # O Explorer só entende as aspas depois da vírgula; nomes de arquivo no Windows não têm aspas
    subprocess.Popen(f'explorer /select,"{path}"')  # noqa: S602,S607 — caminho validado acima
