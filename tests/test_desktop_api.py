"""Testes das rotas novas da API local do app desktop (recorrentes e backup)."""

from datetime import date, timedelta

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from tests.test_desktop_features import temp_db  # noqa: E402,F401 — fixture reaproveitada


@pytest.fixture
def client(temp_db, monkeypatch):  # noqa: F811
    import desktop.api as api

    # Não mexe no config.yaml real durante os testes
    with TestClient(api.app, base_url="http://127.0.0.1") as c:
        yield c


def test_recurring_transaction_and_dashboard(client):
    start = (date.today() - timedelta(weeks=2)).isoformat()
    r = client.post("/api/transactions", json={
        "description": "Aluguel", "amount": 1500, "date": start, "recurring_frequency": "weekly",
    })
    assert r.status_code == 201
    assert r.json()["is_recurring"] is True

    rows = client.get("/api/transactions?days=0").json()
    assert sum(1 for t in rows if t["description"] == "Aluguel") == 3

    upcoming = client.get("/api/dashboard").json()["upcoming_recurring"]
    assert [u["description"] for u in upcoming] == ["Aluguel"]


def test_dashboard_counts_only_until_today(client):
    today = date.today()
    tomorrow = today + timedelta(days=1)
    if tomorrow.month != today.month:
        pytest.skip("último dia do mês: não há dia futuro dentro do mês")
    client.post("/api/transactions", json={"description": "Mercado", "amount": 100, "date": today.isoformat()})
    client.post("/api/transactions", json={"description": "Academia", "amount": 90, "date": tomorrow.isoformat()})

    d = client.get("/api/dashboard").json()
    assert d["summary"]["total_expense"] == 100
    assert d["scheduled"] == {"income": 0, "expense": 90}


def test_budget_hides_income_category(client):
    names = [c["name"] for c in client.get("/api/budget").json()["categories"]]
    assert "Salário" not in names
    assert "Alimentação" in names


def test_budget_counts_more_than_ten_categories(client):
    cats = {c["name"]: c["id"] for c in client.get("/api/categories").json()}
    assert len(cats) > 10
    today = date.today().isoformat()
    # A menor categoria fica fora das 10 maiores do resumo; o orçamento ainda precisa vê-la
    for i, name in enumerate(cats):
        amount = 1 if name == "Outros" else 100 + i
        client.post("/api/transactions", json={
            "description": f"Gasto {i}", "amount": amount, "date": today, "category_name": name,
        })
    client.put(f"/api/categories/{cats['Outros']}/budget", json={"limit": 50})

    outros = next(c for c in client.get("/api/budget").json()["categories"] if c["name"] == "Outros")
    assert outros["spent"] == 1


def test_categorize_ai_uses_local_llm(client, monkeypatch):
    import desktop.routes.finance as finance

    class LocalLLM:
        available = True

        def is_available(self):
            return self.available

        def generate(self, prompt, system_prompt=None):
            return "Alimentação"

    local = LocalLLM()
    monkeypatch.setattr(finance, "get_local_llm_client", lambda: local)
    client.post("/api/transactions", json={"description": "PANIFICADORA BELLA", "amount": 12})
    assert client.get("/api/categorize-ai").json() == {"merchants": 1, "transactions": 1}

    local.available = False
    assert client.post("/api/categorize-ai").status_code == 503

    local.available = True
    r = client.post("/api/categorize-ai").json()
    assert (r["categorized"], r["remaining"]) == (1, 0)
    assert client.get("/api/transactions").json()[0]["category_name"] == "Alimentação"


def test_invalid_frequency_is_rejected(client):
    r = client.post("/api/transactions", json={"description": "X", "amount": 1, "recurring_frequency": "daily"})
    assert r.status_code == 422


def test_backup_routes(client):
    created = client.post("/api/backups")
    assert created.status_code == 201
    name = created.json()["name"]
    assert name in [b["name"] for b in client.get("/api/backups").json()["items"]]

    assert client.post(f"/api/backups/{name}/restore").status_code == 200
    # Só nomes de backup válidos; "../" nem chega a casar com a rota
    assert client.post("/api/backups/config.yaml/restore").status_code == 422
    assert client.post("/api/backups/..%2Fstonks_ai.db/restore").status_code in (404, 405, 422)
    assert client.post("/api/backups/restore-file", content=b"lixo").status_code == 422
