"""Importador dos extratos da Área do Investidor da B3 (investidor.b3.com.br → Extratos).

Dois arquivos, reconhecidos pelo cabeçalho (não pelo nome):

- **Negociação**: compras e vendas, com a data do pregão. Colunas: Data do Negócio,
  Tipo de Movimentação, Mercado, Prazo/Vencimento, Instituição, Código de Negociação,
  Quantidade, Preço, Valor.
- **Movimentação**: proventos e eventos. Colunas: Entrada/Saída, Data, Movimentação,
  Produto, Instituição, Quantidade, Preço unitário, Valor da Operação. Daqui vêm dividendos,
  JCP, rendimentos de FII, desdobramentos e bonificações. As liquidações de compra e venda
  também aparecem aqui, dois dias depois do pregão; elas são ignoradas para não duplicar o
  extrato de Negociação.

Cada linha ganha uma chave (import_key): importar o mesmo período de novo não duplica nada.
"""

import re
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from stonks_ai.collectors.finance.base import FinanceDataError
from stonks_ai.utils.portfolio import is_supported_ticker, normalize_ticker, row_key

SUFFIXES = {".xlsx", ".xls", ".csv"}

NEGOCIACAO = "negociacao"
MOVIMENTACAO = "movimentacao"

_NEGOCIACAO_COLS = {
    "date": "data do negocio",
    "type": "tipo de movimentacao",
    "broker": "instituicao",
    "ticker": "codigo de negociacao",
    "quantity": "quantidade",
    "price": "preco",
    "value": "valor",
}
_MOVIMENTACAO_COLS = {
    "direction": "entrada/saida",
    "date": "data",
    "event": "movimentacao",
    "product": "produto",
    "broker": "instituicao",
    "quantity": "quantidade",
    "price": "preco unitario",
    "value": "valor da operacao",
}

# Movimentação → tipo da operação na carteira
_INCOME_EVENTS = {
    "dividendo": "dividend",
    "juros sobre capital proprio": "jcp",
    "rendimento": "income",
}
_BONUS_EVENTS = {"desdobro", "bonificacao em ativos"}
_TRADE_SETTLEMENT = "transferencia - liquidacao"


def _text(value: Any) -> str:
    """Célula como texto; vazia (NaN) vira ""."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _norm(text: Any) -> str:
    s = unicodedata.normalize("NFKD", _text(text)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()


def _number(value: Any) -> Optional[float]:
    """Número de célula do Excel ou texto pt-BR ("R$ 1.234,56"). "-" e vazio viram None."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).replace("R$", "").replace("\xa0", "").strip()
    if not s or s == "-":
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _date(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, pd.Timestamp):
        return datetime(value.year, value.month, value.day)
    s = _text(value)
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:10], fmt)
        except ValueError:
            continue
    return None


def _read_tables(path: Path) -> List[pd.DataFrame]:
    try:
        if path.suffix.lower() == ".csv":
            return [pd.read_csv(path, header=None, sep=None, engine="python", dtype=str, encoding="utf-8-sig")]
        sheets = pd.read_excel(path, sheet_name=None, header=None)
        return list(sheets.values())
    except Exception as e:
        raise FinanceDataError(f"Não foi possível ler o arquivo: {e}")


def _with_header(df: pd.DataFrame, wanted: Dict[str, str]) -> Optional[Tuple[pd.DataFrame, Dict[str, int]]]:
    """Acha a linha de cabeçalho (nas 10 primeiras) que tem todas as colunas esperadas."""
    for i in range(min(10, len(df))):
        names = [_norm(v) for v in df.iloc[i].tolist()]
        if all(col in names for col in wanted.values()):
            cols = {key: names.index(col) for key, col in wanted.items()}
            return df.iloc[i + 1:].reset_index(drop=True), cols
    return None


def detect(path: Path) -> Tuple[str, pd.DataFrame, Dict[str, int]]:
    for df in _read_tables(path):
        found = _with_header(df, _NEGOCIACAO_COLS)
        if found:
            return NEGOCIACAO, *found
        found = _with_header(df, _MOVIMENTACAO_COLS)
        if found:
            return MOVIMENTACAO, *found
    raise FinanceDataError(
        "Não parece um extrato da B3. Na Área do Investidor, baixe em Excel o extrato de "
        "Negociação (compras e vendas) ou o de Movimentação (proventos e desdobramentos)."
    )


def _keyed(rows: List[Tuple[Tuple, Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Linhas idênticas no mesmo arquivo (duas compras iguais no dia) recebem chaves diferentes."""
    seen: Counter = Counter()
    out = []
    for ident, row in rows:
        seen[ident] += 1
        row["import_key"] = row_key((*ident, seen[ident]))
        out.append(row)
    return out


def _parse_negociacao(df: pd.DataFrame, c: Dict[str, int]) -> Tuple[List[Dict[str, Any]], Counter]:
    rows, skipped = [], Counter()
    for values in df.itertuples(index=False):
        day = _date(values[c["date"]])
        kind_text = _norm(values[c["type"]])
        if day is None or not kind_text:
            continue  # linhas em branco ou de total no fim da planilha
        kind = "buy" if kind_text.startswith("compra") else "sell" if kind_text.startswith("venda") else None
        ticker = normalize_ticker(_text(values[c["ticker"]]))
        qty = _number(values[c["quantity"]])
        price = _number(values[c["price"]])
        if kind is None or not is_supported_ticker(ticker):
            skipped["Opções, termo e outros mercados"] += 1
            continue
        if not qty or not price:
            skipped["Linhas sem quantidade ou preço"] += 1
            continue
        value = _number(values[c["value"]]) or qty * price
        broker = _text(values[c["broker"]])
        ident = (NEGOCIACAO, day.date(), ticker, kind, qty, price, broker)
        rows.append((ident, {
            "ticker": ticker, "kind": kind, "date": day, "quantity": qty, "price": price,
            "fees": 0.0, "amount": round(value, 2), "notes": broker or None,
        }))
    return _keyed(rows), skipped


def _parse_movimentacao(df: pd.DataFrame, c: Dict[str, int]) -> Tuple[List[Dict[str, Any]], Counter]:
    rows, skipped = [], Counter()
    for values in df.itertuples(index=False):
        day = _date(values[c["date"]])
        event = _norm(values[c["event"]])
        if day is None or not event:
            continue
        credit = _norm(values[c["direction"]]).startswith("credito")
        ticker = normalize_ticker(_text(values[c["product"]]).split(" - ")[0])
        qty = _number(values[c["quantity"]]) or 0.0
        price = _number(values[c["price"]]) or 0.0
        value = _number(values[c["value"]])
        broker = _text(values[c["broker"]])

        if event == _TRADE_SETTLEMENT:
            skipped["Compras e vendas (vêm do extrato de Negociação)"] += 1
            continue
        if not is_supported_ticker(ticker):
            skipped["Renda fixa, Tesouro e outros produtos"] += 1
            continue
        if event in _INCOME_EVENTS and credit:
            amount = value if value is not None else qty * price
            if not amount:
                continue
            kind, row = _INCOME_EVENTS[event], {"quantity": 0.0, "price": 0.0, "amount": round(amount, 2)}
        elif event in _BONUS_EVENTS and credit and qty:
            # Desdobro chega sem custo; bonificação, com o custo atribuído por cota
            unit = price if event != "desdobro" else 0.0
            kind, row = "bonus", {"quantity": qty, "price": unit, "amount": round(qty * unit, 2)}
        elif event == "grupamento":
            skipped["Grupamentos (lance à mão em Carteira)"] += 1
            continue
        else:
            skipped["Outros movimentos (aluguel, frações, direitos, transferências)"] += 1
            continue
        ident = (MOVIMENTACAO, day.date(), ticker, kind, event, row["quantity"], row["amount"], broker)
        rows.append((ident, {"ticker": ticker, "kind": kind, "date": day, "fees": 0.0,
                             "notes": broker or None, **row}))
    return _keyed(rows), skipped


def parse(file_path: str) -> Dict[str, Any]:
    """Lê um extrato da B3. Devolve o tipo do arquivo, as operações e o que foi ignorado."""
    path = Path(file_path)
    if path.suffix.lower() not in SUFFIXES:
        raise FinanceDataError("Formato não suportado. Baixe o extrato da B3 em Excel (.xlsx).")
    file_type, df, cols = detect(path)
    parser = _parse_negociacao if file_type == NEGOCIACAO else _parse_movimentacao
    rows, skipped = parser(df, cols)
    return {
        "file_type": file_type,
        "rows": rows,
        "skipped": [{"reason": r, "count": n} for r, n in skipped.most_common()],
    }
