"""Testes dos alertas de preço-alvo (disparo ao cruzar o alvo, pausa entre avisos)."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from stonks_ai import price_alerts
from stonks_ai.database import db
from stonks_ai.models.alert import Alert
from stonks_ai.models.watchlist import WatchlistItem

NOW = datetime(2026, 10, 21, 11, 0)


def add_item(ticker="PETR4", target=40.0, exchange="B3"):
    with db.session() as s:
        item = WatchlistItem(ticker=ticker, exchange=exchange, target_price=target)
        s.add(item)
        s.flush()
        return item.id


def quotes(**prices):
    return lambda ticker, exchange: SimpleNamespace(price=prices[ticker], currency="BRL")


def test_first_check_only_records_the_price():
    add_item(target=40)
    assert price_alerts.check(quotes(PETR4=41), now=NOW) == []   # já acima do alvo: não sabemos se cruzou


def test_alerts_when_price_crosses_up_and_down():
    add_item("PETR4", target=40)
    add_item("VALE3", target=50)
    price_alerts.check(quotes(PETR4=39, VALE3=52), now=NOW)

    got = price_alerts.check(quotes(PETR4=40.5, VALE3=49), now=NOW + timedelta(minutes=5))

    assert [(a["ticker"], a["title"]) for a in got] == [
        ("PETR4", "PETR4 subiu até o preço-alvo"), ("VALE3", "VALE3 caiu até o preço-alvo")]
    assert "R$ 40,50" in got[0]["message"] and "R$ 40,00" in got[0]["message"]
    with db.session() as s:
        assert s.query(Alert).filter(Alert.alert_type == "price_target").count() == 2


def test_quiet_period_after_alert():
    add_item(target=40)
    price_alerts.check(quotes(PETR4=39), now=NOW)
    assert price_alerts.check(quotes(PETR4=41), now=NOW + timedelta(minutes=5))
    price_alerts.check(quotes(PETR4=39), now=NOW + timedelta(minutes=10))
    assert price_alerts.check(quotes(PETR4=41), now=NOW + timedelta(minutes=15)) == []   # oscilando no alvo
    # Passadas 12 horas, o próximo cruzamento (aqui, de volta para baixo) avisa de novo
    later = price_alerts.check(quotes(PETR4=39), now=NOW + timedelta(hours=13))
    assert [a["title"] for a in later] == ["PETR4 caiu até o preço-alvo"]


def test_failed_quote_and_items_without_target_are_skipped():
    add_item(target=40)
    add_item("ITUB4", target=None)

    def broken(ticker, exchange):
        raise RuntimeError("sem internet")

    assert price_alerts.check(broken, now=NOW) == []
    price_alerts.check(quotes(PETR4=39), now=NOW)
    assert price_alerts.check(quotes(PETR4=40), now=NOW + timedelta(minutes=5))   # chegar no alvo conta


def test_reset_forgets_last_price():
    item = add_item(target=40)
    price_alerts.check(quotes(PETR4=39), now=NOW)
    price_alerts.reset(item)
    assert price_alerts.check(quotes(PETR4=41), now=NOW + timedelta(minutes=5)) == []


@pytest.mark.parametrize("when, expected", [
    (datetime(2026, 10, 21, 9, 29), False),
    (datetime(2026, 10, 21, 9, 30), True),
    (datetime(2026, 10, 21, 18, 30), True),
    (datetime(2026, 10, 21, 18, 31), False),
    (datetime(2026, 10, 24, 12, 0), False),   # sábado
])
def test_market_hours(when, expected):
    assert price_alerts.in_market_hours(when) is expected


def test_watchlist_target_change_resets_and_background_settings(monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    import desktop.api as api
    from desktop import autostart
    from stonks_ai.config import config

    saved = {}
    monkeypatch.setattr(config, "set", lambda value, *keys: saved.__setitem__(keys, value))
    monkeypatch.setattr(autostart, "supported", lambda: False)
    item = add_item(target=40)
    price_alerts.check(quotes(PETR4=39), now=NOW)

    with TestClient(api.app, base_url="http://127.0.0.1") as c:
        assert c.patch(f"/api/watchlist/{item}", json={"target_price": 45}).status_code == 200
        assert price_alerts.check(quotes(PETR4=46), now=NOW + timedelta(minutes=5)) == []

        b = c.get("/api/settings/background").json()
        assert b["autostart_supported"] is False and b["start_with_windows"] is False
        r = c.put("/api/settings/background", json={"close_to_tray": False, "start_with_windows": False})
        assert r.status_code == 200
        assert saved[("desktop", "close_to_tray")] is False
        r = c.put("/api/settings/background", json={"close_to_tray": True, "start_with_windows": True})
        assert r.status_code == 422
