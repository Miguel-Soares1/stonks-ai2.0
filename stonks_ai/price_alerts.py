"""
Alertas de preço-alvo da watchlist.

O alerta dispara quando o preço **cruza** o alvo desde a última verificação (de baixo para cima
ou de cima para baixo), não quando simplesmente está acima ou abaixo: assim, um alvo de venda
(acima do preço) e um de compra (abaixo) funcionam sem o usuário dizer qual é qual.

O último preço visto de cada item fica em user_preferences ("price_alert:<id>"), então um
cruzamento enquanto o computador estava desligado é percebido na verificação seguinte.
Depois de avisar, o mesmo item fica quieto por COOLDOWN, para um preço que oscila em
volta do alvo não gerar uma notificação a cada verificação.

Quem chama (desktop/app.py) decide quando verificar e como notificar.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from stonks_ai.database import db
from stonks_ai.models.alert import Alert
from stonks_ai.models.user_preferences import UserPreference
from stonks_ai.models.watchlist import WatchlistItem

PREF_PREFIX = "price_alert:"
COOLDOWN = timedelta(hours=12)
CHECK_INTERVAL_SECONDS = 5 * 60


def in_market_hours(now: datetime) -> bool:
    """Dias úteis, das 9h30 às 18h30 (B3 e o horário da bolsa americana em Brasília)."""
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return 9 * 60 + 30 <= minutes <= 18 * 60 + 30


def _load_state(session, item_id: int) -> Dict[str, Any]:
    pref = session.query(UserPreference).filter(UserPreference.key == f"{PREF_PREFIX}{item_id}").first()
    try:
        return json.loads(pref.value) if pref else {}
    except ValueError:
        return {}


def _save_state(session, item_id: int, state: Dict[str, Any]) -> None:
    key = f"{PREF_PREFIX}{item_id}"
    pref = session.query(UserPreference).filter(UserPreference.key == key).first()
    if pref:
        pref.value = json.dumps(state)
    else:
        session.add(UserPreference(key=key, value=json.dumps(state)))


def reset(item_id: int) -> None:
    """Esquece o último preço visto (alvo mudou ou item saiu da watchlist)."""
    with db.session() as s:
        s.query(UserPreference).filter(UserPreference.key == f"{PREF_PREFIX}{item_id}").delete()


def _money(value: float, currency: str) -> str:
    symbol = "US$" if currency == "USD" else "R$"
    return f"{symbol} " + f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def check(fetch: Callable[[str, str], Any], now: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Verifica os itens com preço-alvo e devolve os que cruzaram o alvo (já gravados em Alertas).

    fetch(ticker, exchange) devolve um objeto com .price e .currency (a cotação do agente).
    Cotação que falha é ignorada nesta rodada.
    """
    now = now or datetime.now()
    with db.session() as s:
        items = [(i.id, i.ticker, i.exchange, i.target_price)
                 for i in s.query(WatchlistItem).filter(WatchlistItem.target_price.isnot(None)).all()]

    triggered = []
    for item_id, ticker, exchange, target in items:
        try:
            quote = fetch(ticker, exchange)
            price, currency = float(quote.price), getattr(quote, "currency", "BRL") or "BRL"
        except Exception:
            continue
        if not price:
            continue
        with db.session() as s:
            state = _load_state(s, item_id)
            last = state.get("last")
            notified = state.get("notified")
            crossed = last is not None and (last < target <= price or last > target >= price)
            quiet = notified and now - datetime.fromisoformat(notified) < COOLDOWN
            if crossed and not quiet:
                up = price >= target
                title = f"{ticker} {'subiu' if up else 'caiu'} até o preço-alvo"
                message = (f"{ticker} está em {_money(price, currency)}; o alvo era {_money(target, currency)}. "
                           "Edite ou remova o alvo na Watchlist.")
                s.add(Alert(alert_type="price_target", title=title, message=message, severity="warning",
                            data=json.dumps({"ticker": ticker, "price": price, "target": target})))
                state["notified"] = now.isoformat(timespec="seconds")
                triggered.append({"ticker": ticker, "price": price, "target": target, "title": title, "message": message})
            state["last"] = price
            _save_state(s, item_id, state)
    return triggered
