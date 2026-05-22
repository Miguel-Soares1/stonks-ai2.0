"""
Utilitários de formatação para exibição de dados financeiros.

Formata moeda, percentuais, datas, números grandes, etc.
"""

import copy
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def format_currency(
    value: Optional[float],
    currency: str = "BRL",
    include_symbol: bool = True,
) -> str:
    """Formata valor monetário."""
    if value is None:
        return "N/A"

    if currency == "BRL":
        symbol = "R$" if include_symbol else ""
        return f"{symbol} {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    else:
        symbol = "$" if include_symbol else ""
        return f"{symbol} {value:,.2f}"


def format_percent(value: Optional[float], decimals: int = 2, is_decimal: bool = True) -> str:
    """Formata valor percentual.

    Args:
        value: Valor a ser formatado.
        decimals: Número de casas decimais.
        is_decimal: Se True (padrão), assume que 0.15 = 15%.
                     Se False, assume que o valor já está em percentual (ex: 15 = 15%).
    """
    if value is None:
        return "N/A"
    if is_decimal:
        value = value * 100
    return f"{value:,.{decimals}f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def format_large_number(value: Optional[Union[int, float]]) -> str:
    """Formata números grandes (ex: 1.5B, 2.3M)."""
    if value is None:
        return "N/A"

    try:
        value = float(value)
        if abs(value) >= 1_000_000_000_000:
            return f"{value / 1_000_000_000_000:.1f}T"
        elif abs(value) >= 1_000_000_000:
            return f"{value / 1_000_000_000:.1f}B"
        elif abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"
        elif abs(value) >= 1_000:
            return f"{value / 1_000:.1f}K"
        else:
            return f"{value:,.0f}"
    except (ValueError, TypeError):
        return "N/A"


def format_change(change: Optional[float], percent: Optional[float] = None) -> str:
    """Formata variação com sinal e cor (indicador textual)."""
    if change is None:
        return "N/A"

    signal = "+" if change > 0 else ""
    result = f"{signal}{change:.2f}"
    if percent is not None:
        result += f" ({signal}{percent:.2f}%)"
    return result


def format_ticker_display(ticker: str, exchange: str) -> str:
    """Formata ticker para exibição."""
    ticker = ticker.upper().replace(".SA", "")
    exchange_label = "B3" if "B3" in exchange.upper() else "NYSE"
    return f"{ticker} ({exchange_label})"


def format_timestamp(dt: Optional[datetime], fmt: str = "%d/%m/%Y %H:%M") -> str:
    """Formata timestamp para exibição."""
    if dt is None:
        return "N/A"
    return dt.strftime(fmt)


def format_brief(quote_data: Dict[str, Any]) -> str:
    """Formata resumo compacto de cotação."""
    ticker = quote_data.get("ticker", "???")
    price = quote_data.get("price", 0)
    change = quote_data.get("change_percent", 0)

    signal = "🔺" if change > 0 else "🔻" if change < 0 else "➡️"
    return f"{ticker}: {price:.2f} {signal} {change:+.2f}%"


def build_stock_table_rows(
    quotes: List[Dict[str, Any]],
    fundamentals: Optional[List[Optional[Dict[str, Any]]]] = None,
) -> List[List[str]]:
    """
    Constrói linhas para tabela de ações formatada.

    Retorna lista de listas no formato:
    [Ticker, Preço, Variação, P/L, DY, Máx, Mín, Vol]
    """
    rows = []
    for i, q in enumerate(quotes):
        change = q.get("change_percent", 0)
        change_str = f"{change:+.2f}% 🔺" if change > 0 else f"{change:+.2f}% 🔻" if change < 0 else "0.00% ➡️"

        fund = fundamentals[i] if fundamentals and i < len(fundamentals) else None

        row = [
            q.get("ticker", "N/A"),
            f"{q.get('price', 0):.2f}",
            change_str,
            format_percent(fund.get("dividend_yield") if fund else None) if fund else "N/A",
            format_large_number(q.get("volume", 0)) if q.get("volume") else "N/A",
        ]
        rows.append(row)

    return rows


def _mask_user_path(value: str) -> str:
    """Substitui o caminho absoluto do usuário por um placeholder seguro.

    Ex: C:\\Users\\username\\... -> ~\\...\\
    """
    if not isinstance(value, str):
        return value

    user_home = Path.home()

    # Tenta converter para caminho relativo ao home directory
    try:
        p = Path(value)
        relative = p.relative_to(user_home)
        return "~" / relative
    except (ValueError, TypeError):
        pass

    # Fallback: regex para Windows — C:\Users\NOME\... -> ~\...\
    win_user_pattern = re.compile(
        r"([a-zA-Z]:\\?)[Uu]sers\\[^\\]+\\?",
    )
    result = win_user_pattern.sub(r"~\...\\", value, count=1)

    # Fallback: regex para Unix — /home/NOME/... -> ~/.../
    unix_user_pattern = re.compile(
        r"/home/[^/\s]+/?",
    )
    result = unix_user_pattern.sub(r"~/.../", result, count=1)

    return result


def sanitize_config_for_display(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """Retorna uma cópia da config com caminhos pessoais mascarados.

    Remove ou substitui informações como caminhos absolutos contendo
    o nome de usuário do sistema, antes de exibir em tela.

    Args:
        config_data: Dicionário completo de configuração.

    Returns:
        Cópia do dicionário com caminhos sanitizados.
    """
    sanitized = copy.deepcopy(config_data)

    # Sanitiza database.path se existir
    db_path = sanitized.get("database", {}).get("path")
    if db_path:
        sanitized["database"]["path"] = _mask_user_path(db_path)

    return sanitized
