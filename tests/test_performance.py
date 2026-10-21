"""Testes da rentabilidade ponderada no tempo (docs/CARTEIRA.md, seção 5)."""

from datetime import date, datetime
from types import SimpleNamespace

import pytest

from stonks_ai.models.investment import InvestmentOperation
from stonks_ai.utils import performance, portfolio


def op(kind, day, ticker="XPTO3", qty=0.0, price=0.0, fees=0.0, amount=0.0):
    return InvestmentOperation(ticker=ticker, kind=kind, date=datetime(*day),
                               quantity=qty, price=price, fees=fees, amount=amount)


D0, D1, D2, D3 = date(2025, 1, 2), date(2025, 6, 27), date(2025, 6, 30), date(2025, 12, 30)


def test_example_from_the_docs_is_13_percent_not_3_6():
    # R$ 1.000 rendem 10%; aporte de R$ 10.000; o total rende 11.400 / 11.100 até dezembro
    new_shares = 10_000 / 11
    ops = [op("buy", (2025, 1, 2), qty=100, price=10), op("buy", (2025, 6, 30), qty=new_shares, price=11)]
    prices = {"XPTO3": {D0: 10.0, D1: 11.0, D2: 11.0, D3: 11_400 / (100 + new_shares)}}

    index, missing = performance.portfolio_index(ops, [D0, D1, D2, D3], prices)

    assert missing == []
    assert index[1] == pytest.approx(1.10)
    assert index[-1] == pytest.approx(1.10 * 11_400 / 11_100)   # +13,0%


def test_sells_and_dividends_are_not_losses():
    days = [D0, D1, D2]
    ops = [
        op("buy", (2025, 1, 2), qty=100, price=10),
        op("dividend", (2025, 6, 27), amount=50),                   # 5% em proventos
        op("sell", (2025, 6, 30), qty=100, price=10),               # resgata tudo ao mesmo preço
    ]
    prices = {"XPTO3": {D0: 10.0, D1: 10.0, D2: 10.0}}
    index, _ = performance.portfolio_index(ops, days, prices)
    assert index == pytest.approx([1.0, 1.05, 1.05])


def test_split_does_not_look_like_a_gain():
    # yfinance devolve o preço anterior ao desdobramento 1:2 já dividido por 2
    closes = {D0: 5.0, D1: 5.0, D2: 5.0}
    raw = performance.unadjust_splits(closes, {D1: 2.0})
    assert raw == {D0: 10.0, D1: 5.0, D2: 5.0}

    ops = [op("buy", (2025, 1, 2), qty=100, price=10), op("bonus", (2025, 6, 27), qty=100)]
    index, _ = performance.portfolio_index(ops, [D0, D1, D2], {"XPTO3": raw})
    assert index == pytest.approx([1.0, 1.0, 1.0])


def test_asset_without_history_uses_trade_price():
    ops = [op("buy", (2025, 1, 2), ticker="VELH3", qty=10, price=20)]
    index, missing = performance.portfolio_index(ops, [D0, D1], {"VELH3": {}})
    assert missing == ["VELH3"]
    assert index == [1.0, 1.0]


def test_cdi_accrues_every_business_day_between_sessions():
    days = [date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 6)]
    rates = {date(2025, 1, 2): 0.05, date(2025, 1, 3): 0.05}
    idx = performance.cdi_index(days, rates)
    assert idx == pytest.approx([1.0, 1.0005, 1.0005 ** 2])


def test_windows_and_share_of_cdi():
    days = [date(2024, 12, 31), date(2025, 6, 30), date(2025, 10, 20)]
    ops = [op("buy", (2024, 12, 31), qty=100, price=10)]
    prices = {"XPTO3": {days[0]: 10.0, days[1]: 10.5, days[2]: 11.0}}
    rates = {days[0]: 0.04, days[1]: 0.04}
    ibov = {days[0]: 100.0, days[1]: 104.0, days[2]: 108.0}

    r = performance.build(ops, days, prices, rates, ibov, today=date(2025, 10, 20))

    by_key = {w["key"]: w for w in r["windows"]}
    assert by_key["start"]["portfolio"] == 10.0
    assert by_key["start"]["ibov"] == 8.0
    assert by_key["ytd"]["portfolio"] == 10.0
    assert "12m" not in by_key                     # a carteira começou há menos de 12 meses
    assert by_key["start"]["cdi_share"] == round(10.0 / by_key["start"]["cdi"] * 100)
    assert [p["portfolio"] for p in r["chart"]] == [0.0, 10.0]   # um ponto por semana + o último


def test_overview_without_internet_still_answers():
    portfolio.add_operation("PETR4", "buy", date(2025, 1, 2), quantity=10, price=30)

    def offline(*_):
        raise RuntimeError("sem internet")

    r = performance.overview(fetch_closes=offline, fetch_cdi=offline, today=date(2025, 1, 10))
    assert r["benchmarks"] == {"cdi": False, "ibov": False}
    assert r["without_history"] == ["PETR4"]
    assert r["windows"][0]["portfolio"] == 0.0


def test_overview_with_fake_data():
    portfolio.add_operation("PETR4", "buy", date(2025, 1, 2), quantity=10, price=30)
    days = [date(2025, 1, 2), date(2025, 1, 3)]

    def closes(symbol, start):
        if symbol == "^BVSP":
            return {days[0]: 100.0, days[1]: 101.0}, {}
        return {days[0]: 30.0, days[1]: 33.0}, {}

    r = performance.overview(fetch_closes=closes, fetch_cdi=lambda s, e: {days[0]: 0.05},
                             today=date(2025, 1, 3))
    start = r["windows"][0]
    assert (start["portfolio"], start["ibov"], start["cdi"]) == (10.0, 1.0, 0.05)
    assert performance.overview(fetch_closes=closes, fetch_cdi=lambda s, e: {}) is not None


def test_crypto_history_is_converted_to_reais():
    portfolio.add_operation("BTC", "buy", date(2025, 1, 2), quantity=0.01, price=600_000)
    days = [date(2025, 1, 2), date(2025, 1, 3)]
    asked = []

    def closes(symbol, start):
        asked.append(symbol)
        if symbol == "^BVSP":
            return {days[0]: 100.0, days[1]: 100.0}, {}
        if symbol == "BRL=X":
            return {days[0]: 6.0, days[1]: 6.0}, {}
        return {days[0]: 100_000.0, days[1]: 110_000.0}, {}   # BTC-USD

    r = performance.overview(fetch_closes=closes, fetch_cdi=lambda s, e: {}, today=date(2025, 1, 3))
    assert "BTC-USD" in asked and "BTC.SA" not in asked
    assert r["without_history"] == []
    assert r["windows"][0]["portfolio"] == 10.0                # 600 mil -> 660 mil em reais


def test_performance_route(monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    import desktop.api as api

    monkeypatch.setattr(api, "migrate_plaintext_key", lambda cfg: False)
    with TestClient(api.app, base_url="http://127.0.0.1") as c:
        assert c.get("/api/portfolio/performance").json() is None
        portfolio.add_operation("PETR4", "buy", date(2025, 1, 2), quantity=10, price=30)
        monkeypatch.setattr(performance, "overview", lambda: {"windows": [], "chart": []})
        assert c.get("/api/portfolio/performance").json() == {"windows": [], "chart": []}
