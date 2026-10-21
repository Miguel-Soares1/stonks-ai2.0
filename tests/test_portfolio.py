"""Testes da carteira de investimentos: preço médio, proventos, importação da B3 e rotas."""

from datetime import date, datetime
from types import SimpleNamespace

import pandas as pd
import pytest

from stonks_ai.collectors.finance import b3_importer
from stonks_ai.collectors.finance.base import FinanceDataError
from stonks_ai.models.investment import InvestmentOperation
from stonks_ai.utils import portfolio


def op(kind, ticker="PETR4", day=(2025, 1, 10), qty=0.0, price=0.0, fees=0.0, amount=0.0, id=None):
    return InvestmentOperation(id=id, ticker=ticker, kind=kind, date=datetime(*day),
                               quantity=qty, price=price, fees=fees, amount=amount)


@pytest.fixture(autouse=True)
def no_quote_cache():
    portfolio.clear_quote_cache()
    yield
    portfolio.clear_quote_cache()


# ── Cálculo das posições ────────────────────────────────────────────────

def test_average_price_includes_fees_and_sells_keep_it():
    p = portfolio.build_positions([
        op("buy", qty=100, price=10, fees=5, day=(2025, 1, 2)),
        op("buy", qty=100, price=20, fees=5, day=(2025, 2, 3)),
        op("sell", qty=50, price=30, fees=2, day=(2025, 3, 4)),
    ])["PETR4"]
    assert p.quantity == 150
    assert p.avg_price == pytest.approx(15.05)          # (1000 + 5 + 2000 + 5) / 200
    assert p.realized == pytest.approx(50 * 30 - 2 - 50 * 15.05)
    assert p.cost == pytest.approx(150 * 15.05)


def test_split_and_bonus_change_quantity_not_cost():
    p = portfolio.build_positions([
        op("buy", qty=100, price=30, day=(2025, 1, 2)),
        op("bonus", qty=100, price=0, day=(2025, 2, 1)),     # desdobro 1:2
        op("bonus", qty=10, price=5, day=(2025, 3, 1)),      # bonificação com custo atribuído
        op("grouping", qty=105, day=(2025, 4, 1)),           # grupamento 2:1
    ])["PETR4"]
    assert p.quantity == 105
    assert p.cost == pytest.approx(3000 + 50)


def test_selling_more_than_known_marks_incomplete():
    p = portfolio.build_positions([
        op("buy", qty=10, price=10, day=(2025, 1, 2)),
        op("sell", qty=30, price=12, day=(2025, 2, 2)),
    ])["PETR4"]
    assert p.incomplete
    assert p.quantity == 0
    assert p.realized == pytest.approx(10 * 12 - 10 * 10)  # só as cotas conhecidas


def test_same_day_buy_is_applied_before_sell():
    p = portfolio.build_positions([
        op("sell", qty=10, price=11, day=(2025, 1, 2), id=1),
        op("buy", qty=10, price=10, day=(2025, 1, 2), id=2),
    ])["PETR4"]
    assert not p.incomplete
    assert p.realized == pytest.approx(10)


def test_income_totals_and_last_12_months():
    ops = [
        op("buy", ticker="HGLG11", qty=10, price=160, day=(2024, 1, 5)),
        op("income", ticker="HGLG11", amount=11, day=(2024, 6, 14)),
        op("income", ticker="HGLG11", amount=12, day=(2025, 9, 14)),
        op("jcp", ticker="HGLG11", amount=3, day=(2025, 10, 1)),
    ]
    p = portfolio.build_positions(ops, today=date(2025, 10, 21))["HGLG11"]
    assert p.income == 26
    assert p.income_12m == 15
    months = portfolio.income_by_month(ops, today=date(2025, 10, 21))
    assert len(months) == 12
    assert months[-1] == {"year": 2025, "month": 10, "amount": 3}
    assert months[-2]["amount"] == 12


def test_normalize_ticker():
    assert portfolio.normalize_ticker("petr4f") == "PETR4"
    assert portfolio.normalize_ticker("VALE3.SA") == "VALE3"
    assert portfolio.normalize_ticker("HGLG11") == "HGLG11"
    assert not portfolio.is_supported_ticker("AAPL")
    assert portfolio.is_supported_ticker("AAPL34")


# ── Operações no banco ──────────────────────────────────────────────────

def test_add_operation_validates():
    with pytest.raises(portfolio.PortfolioError, match="não é um código da B3"):
        portfolio.add_operation("AAPL", "buy", date(2025, 1, 2), quantity=1, price=10)
    with pytest.raises(portfolio.PortfolioError, match="futuro"):
        portfolio.add_operation("PETR4", "buy", date(2999, 1, 2), quantity=1, price=10)
    with pytest.raises(portfolio.PortfolioError, match="preço"):
        portfolio.add_operation("PETR4", "buy", date(2025, 1, 2), quantity=1)
    portfolio.add_operation("PETR4", "buy", date(2025, 1, 2), quantity=5, price=10)
    with pytest.raises(portfolio.PortfolioError, match="5 cotas"):
        portfolio.add_operation("PETR4", "sell", date(2025, 2, 2), quantity=6, price=10)


def test_overview_uses_quotes_and_falls_back_to_cost():
    portfolio.add_operation("PETR4", "buy", date(2025, 1, 2), quantity=100, price=30)
    portfolio.add_operation("HGLG11", "buy", date(2025, 1, 2), quantity=10, price=150)
    portfolio.add_operation("HGLG11", "income", date(2025, 2, 14), amount=11)

    def fetch(ticker):
        if ticker == "HGLG11":
            raise RuntimeError("sem internet")
        return SimpleNamespace(price=36.0, change_percent=1.5, name="Petrobras")

    o = portfolio.overview(fetch=fetch)
    rows = {r["ticker"]: r for r in o["positions"]}
    assert rows["PETR4"]["market_value"] == 3600
    assert rows["PETR4"]["result"] == 600
    assert rows["PETR4"]["result_percent"] == 20
    assert rows["HGLG11"]["price"] is None
    assert rows["HGLG11"]["market_value"] == 1500          # pelo custo
    t = o["totals"]
    assert t["market_value"] == 5100
    assert t["result"] == 600                              # só o que tem cotação
    assert t["missing_quotes"] == 1
    assert t["income_total"] == 11
    assert sum(r["weight"] for r in o["positions"]) == pytest.approx(100)


# ── Criptomoedas ────────────────────────────────────────────────────────

def test_crypto_tickers():
    assert portfolio.normalize_ticker("btc") == "BTC"
    assert portfolio.normalize_ticker("eth-usd") == "ETH"
    assert portfolio.normalize_ticker("SOL-BRL") == "SOL"
    assert not portfolio.is_supported_ticker("BTC")      # o importador da B3 continua só com a bolsa


def test_crypto_operations_in_fractions():
    portfolio.add_operation("btc", "buy", date(2025, 1, 2), quantity=0.0035, price=600_000, fees=4.5)
    portfolio.add_operation("BTC", "sell", date(2025, 3, 2), quantity=0.001, price=550_000)
    p = portfolio.build_positions(portfolio.list_operations())["BTC"]
    assert p.quantity == pytest.approx(0.0025)
    assert p.avg_price == pytest.approx((0.0035 * 600_000 + 4.5) / 0.0035)
    with pytest.raises(portfolio.PortfolioError, match="0.0025 BTC"):
        portfolio.add_operation("BTC", "sell", date(2025, 4, 2), quantity=0.003, price=500_000)
    with pytest.raises(portfolio.PortfolioError, match="só compras e vendas"):
        portfolio.add_operation("ETH", "dividend", date(2025, 4, 2), amount=10)
    with pytest.raises(portfolio.PortfolioError, match="criptomoedas aceitas"):
        portfolio.add_operation("UNI", "buy", date(2025, 4, 2), quantity=1, price=10)


def test_overview_marks_crypto_and_uses_its_quote():
    portfolio.add_operation("ETH", "buy", date(2025, 1, 2), quantity=0.5, price=12_000)
    o = portfolio.overview(fetch=lambda t: SimpleNamespace(price=13_000.0, change_percent=-2.0, name=""))
    eth = o["positions"][0]
    assert eth["crypto"] is True
    assert eth["name"] == "Ethereum"                      # sem nome na cotação, vem da lista
    assert eth["market_value"] == 6500


def test_crypto_prices_in_reais_use_last_known_exchange_rate():
    from stonks_ai.collectors import crypto

    usd = {date(2025, 1, 3): 100.0, date(2025, 1, 4): 110.0, date(2025, 1, 6): 120.0}   # 4/1 é sábado
    fx = {date(2025, 1, 2): 6.0, date(2025, 1, 3): 6.1, date(2025, 1, 6): 6.2}
    assert crypto.to_brl(usd, fx) == {
        date(2025, 1, 3): pytest.approx(610.0),
        date(2025, 1, 4): pytest.approx(671.0),           # câmbio de sexta
        date(2025, 1, 6): pytest.approx(744.0),
    }
    assert crypto.to_brl({date(2025, 1, 1): 1.0}, fx) == {}   # antes do primeiro câmbio conhecido


# ── Importação da B3 ────────────────────────────────────────────────────

NEGOCIACAO_HEADER = ["Data do Negócio", "Tipo de Movimentação", "Mercado", "Prazo/Vencimento",
                     "Instituição", "Código de Negociação", "Quantidade", "Preço", "Valor"]
MOVIMENTACAO_HEADER = ["Entrada/Saída", "Data", "Movimentação", "Produto", "Instituição",
                       "Quantidade", "Preço unitário", "Valor da Operação"]


def write_xlsx(path, header, rows):
    pd.DataFrame(rows, columns=header).to_excel(path, index=False)
    return str(path)


@pytest.fixture
def negociacao(tmp_path):
    return write_xlsx(tmp_path / "negociacao-2025.xlsx", NEGOCIACAO_HEADER, [
        ["02/01/2025", "Compra", "Mercado à Vista", "-", "XP INVESTIMENTOS", "PETR4", 100, 30.5, 3050],
        ["02/01/2025", "Compra", "Mercado Fracionário", "-", "XP INVESTIMENTOS", "PETR4F", 7, 30.5, 213.5],
        ["02/01/2025", "Compra", "Mercado Fracionário", "-", "XP INVESTIMENTOS", "PETR4F", 7, 30.5, 213.5],
        ["10/03/2025", "Venda", "Mercado à Vista", "-", "XP INVESTIMENTOS", "PETR4", 14, 35, 490],
        ["11/03/2025", "Compra", "Opção de Compra", "-", "XP INVESTIMENTOS", "PETRC350", 100, 0.5, 50],
    ])


@pytest.fixture
def movimentacao(tmp_path):
    return write_xlsx(tmp_path / "movimentacao-2025.xlsx", MOVIMENTACAO_HEADER, [
        ["Credito", "04/01/2025", "Transferência - Liquidação", "PETR4 - PETROLEO BRASILEIRO S.A. PETROBRAS", "XP", 100, 30.5, 3050],
        ["Credito", "20/02/2025", "Dividendo", "PETR4 - PETROLEO BRASILEIRO S.A. PETROBRAS", "XP", 114, 0.5, 57],
        ["Credito", "20/02/2025", "Juros Sobre Capital Próprio", "PETR4 - PETROLEO BRASILEIRO S.A. PETROBRAS", "XP", 114, "-", "R$ 12,34"],
        ["Credito", "15/03/2025", "Rendimento", "HGLG11 - CSHG LOGISTICA FDO INV IMOB", "XP", 10, 1.1, 11],
        ["Credito", "01/04/2025", "Desdobro", "PETR4 - PETROLEO BRASILEIRO S.A. PETROBRAS", "XP", 100, "-", "-"],
        ["Credito", "02/04/2025", "Bonificação em Ativos", "ITSA4 - ITAUSA S.A.", "XP", 5, 18.2, 91],
        ["Credito", "05/04/2025", "Juros", "Tesouro Selic 2029", "XP", 1, "-", 40],
        ["Debito", "06/04/2025", "Grupamento", "MGLU3 - MAGAZINE LUIZA S.A.", "XP", 90, "-", "-"],
        ["Credito", "07/04/2025", "Empréstimo", "PETR4 - PETROLEO BRASILEIRO S.A. PETROBRAS", "XP", 50, "-", "-"],
    ])


def test_parse_negociacao(negociacao):
    r = b3_importer.parse(negociacao)
    assert r["file_type"] == "negociacao"
    rows = r["rows"]
    assert [(x["kind"], x["ticker"], x["quantity"]) for x in rows] == [
        ("buy", "PETR4", 100), ("buy", "PETR4", 7), ("buy", "PETR4", 7), ("sell", "PETR4", 14)]
    assert len({x["import_key"] for x in rows}) == 4    # as duas compras iguais continuam duas
    assert r["skipped"] == [{"reason": "Opções, termo e outros mercados", "count": 1}]


def test_parse_movimentacao(movimentacao):
    r = b3_importer.parse(movimentacao)
    assert r["file_type"] == "movimentacao"
    got = [(x["kind"], x["ticker"], x["quantity"], x["price"], x["amount"]) for x in r["rows"]]
    assert got == [
        ("dividend", "PETR4", 0, 0, 57),
        ("jcp", "PETR4", 0, 0, 12.34),
        ("income", "HGLG11", 0, 0, 11),
        ("bonus", "PETR4", 100, 0, 0),
        ("bonus", "ITSA4", 5, 18.2, 91),
    ]
    reasons = {s["reason"] for s in r["skipped"]}
    assert "Compras e vendas (vêm do extrato de Negociação)" in reasons
    assert "Grupamentos (lance à mão em Carteira)" in reasons
    assert "Renda fixa, Tesouro e outros produtos" in reasons


def test_parse_header_below_title_rows(tmp_path):
    path = tmp_path / "negociacao.xlsx"
    rows = [["Extrato de negociação"] + [None] * 8, [None] * 9, NEGOCIACAO_HEADER,
            ["02/01/2025", "Compra", "Mercado à Vista", "-", "XP", "VALE3", 10, 60, 600]]
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    assert b3_importer.parse(str(path))["rows"][0]["ticker"] == "VALE3"


def test_parse_rejects_bank_statement(tmp_path):
    path = write_xlsx(tmp_path / "extrato.xlsx", ["Data", "Descrição", "Valor"], [["02/01/2025", "Mercado", -50]])
    with pytest.raises(FinanceDataError, match="extrato da B3"):
        b3_importer.parse(path)


# ── Rotas ───────────────────────────────────────────────────────────────

@pytest.fixture
def client(monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    import desktop.api as api

    monkeypatch.setattr(portfolio, "_default_fetch",
                        lambda t: SimpleNamespace(price=40.0, change_percent=0.0, name=t))
    with TestClient(api.app, base_url="http://127.0.0.1") as c:
        yield c


def test_import_twice_does_not_duplicate(client, negociacao, movimentacao):
    with open(negociacao, "rb") as f:
        content = f.read()
    r = client.post("/api/portfolio/import?filename=negociacao-2025.xlsx", content=content).json()
    assert (r["file_type"], r["imported"], r["duplicates"]) == ("negociacao", 4, 0)
    r = client.post("/api/portfolio/import?filename=negociacao-2025.xlsx", content=content).json()
    assert (r["imported"], r["duplicates"]) == (0, 4)

    with open(movimentacao, "rb") as f:
        client.post("/api/portfolio/import?filename=movimentacao-2025.xlsx", content=f.read())

    o = client.get("/api/portfolio").json()
    petr = next(p for p in o["positions"] if p["ticker"] == "PETR4")
    assert petr["quantity"] == 100 + 7 + 7 - 14 + 100     # compras, venda e desdobro
    assert petr["income"] == pytest.approx(57 + 12.34)
    assert o["totals"]["operation_count"] == 9


def test_import_rejects_other_files(client):
    r = client.post("/api/portfolio/import?filename=extrato.pdf", content=b"%PDF")
    assert r.status_code == 422


def test_manual_operation_routes(client):
    r = client.post("/api/portfolio/operations", json={
        "ticker": "bova11", "kind": "buy", "date": "2025-01-02", "quantity": 10, "price": 120, "fees": 1})
    assert r.status_code == 201
    op_id = r.json()["id"]
    assert r.json()["ticker"] == "BOVA11"

    r = client.post("/api/portfolio/operations", json={
        "ticker": "BOVA11", "kind": "sell", "date": "2025-02-02", "quantity": 11, "price": 130})
    assert r.status_code == 422

    o = client.get("/api/portfolio").json()
    assert o["positions"][0]["avg_price"] == pytest.approx(120.1)
    assert o["totals"]["market_value"] == 400

    assert client.delete(f"/api/portfolio/operations/{op_id}").status_code == 204
    assert client.get("/api/portfolio").json()["positions"] == []
    assert client.delete(f"/api/portfolio/operations/{op_id}").status_code == 404
