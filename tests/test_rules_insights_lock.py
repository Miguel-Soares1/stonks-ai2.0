"""Testes da categorização por regras, dos insights do mês e do bloqueio por PIN."""

from datetime import date

import pytest

from stonks_ai.collectors.finance import categorizer as cat_mod
from stonks_ai.collectors.finance.categorizer import Categorizer, merchant_key
from stonks_ai.utils import insights
from tests.test_desktop_features import agent, temp_db  # noqa: F401 — fixtures reaproveitadas


@pytest.fixture(autouse=True)
def fresh_categorizer_cache():
    cat_mod.invalidate_cache()
    yield
    cat_mod.invalidate_cache()


# ── Categorização ───────────────────────────────────────────────────────

class TestMerchantKey:
    @pytest.mark.parametrize("description, key", [
        ("PANVEL FARMACIAS LJ 33", "PANVEL FARMACIAS"),
        ("COMPRA CARTAO PANVEL FARMACIAS LJ 33 20/10", "PANVEL FARMACIAS"),
        ("UBER *TRIP 8842", "UBER TRIP"),
        ("Padaria São João", "PADARIA JOAO"),
        ("12345", ""),
    ])
    def test_keys(self, description, key):
        assert merchant_key(description) == key


class TestCategorizer:
    def test_keyword_is_a_whole_word(self, agent):  # noqa: F811
        c = Categorizer()
        assert c.categorize("DOCES DA VOVO")[1] == "Outros"  # "DOC" não casa com "DOCES"
        assert c.categorize("TED ENVIADA JOAO")[1] == "Transferências"
        assert c.categorize("FARMACIAS SAO PAULO")[1] == "Saúde"  # plural casa
        assert c.categorize("Farmácia Popular")[1] == "Saúde"  # acento não atrapalha

    def test_most_specific_keyword_wins(self, agent):  # noqa: F811
        c = Categorizer()
        # "SUPERMERCADO" (Alimentação) é mais específico que "MERCADO"; ambos Alimentação,
        # então testamos com duas categorias concorrentes:
        assert c.categorize("POSTO SHELL AMAZON PRIME")[1] == "Assinaturas"  # "AMAZON PRIME" > "POSTO"

    def test_correction_creates_rule_and_fixes_same_merchant(self, agent):  # noqa: F811
        a = agent.add_transaction("CPFL PAULISTA FATURA 09", 200)
        b = agent.add_transaction("CPFL PAULISTA FATURA 10", 210)
        other = agent.add_transaction("NETFLIX", 40)
        assert a["category_name"] == "Moradia"  # CPFL é palavra-chave de Moradia

        updated = agent.update_transaction(a["id"], category_name="Outros")
        assert updated["also_recategorized"] == 1  # b era do mesmo estabelecimento e categoria
        names = {t["id"]: t["category_name"] for t in agent.list_transactions(limit=10)}
        assert names[b["id"]] == "Outros"
        assert names[other["id"]] == "Assinaturas"

        # A regra vence a palavra-chave nas próximas
        assert agent.add_transaction("CPFL PAULISTA FATURA 11", 220)["category_name"] == "Outros"
        assert Categorizer.list_rules() == [{"merchant": "CPFL PAULISTA FATURA", "category": "Outros"}]

    def test_unchanged_category_does_not_learn(self, agent):  # noqa: F811
        tx = agent.add_transaction("NETFLIX", 40)
        assert agent.update_transaction(tx["id"], category_name="Assinaturas", notes="x")["also_recategorized"] == 0
        assert Categorizer.list_rules() == []

    def test_importer_uses_learned_rules(self, agent, tmp_path):  # noqa: F811
        tx = agent.add_transaction("PANVEL FARMACIAS LJ 1", 30, category_name="Lazer")
        agent.update_transaction(tx["id"], category_name="Saúde")
        csv = tmp_path / "extrato.csv"
        csv.write_text("data,descricao,valor\n2026-10-01,PANVEL FARMACIAS LJ 99,-45.90\n", encoding="utf-8")
        result = agent.import_file(str(csv))
        assert result["imported"] == 1, result
        imported = [t for t in agent.list_transactions(limit=10, days=None) if t["description"].endswith("LJ 99")]
        assert imported[0]["category_name"] == "Saúde"

    def test_delete_rule(self, agent):  # noqa: F811
        tx = agent.add_transaction("LOJA DO ZE", 10)
        agent.update_transaction(tx["id"], category_name="Lazer")
        assert Categorizer.delete_rule("ZE")
        assert Categorizer.list_rules() == []


# ── Insights ────────────────────────────────────────────────────────────

class TestInsights:
    def test_category_increase_same_period(self, agent):  # noqa: F811
        today = date(2026, 10, 20)
        agent.add_transaction("IFOOD", 100, date="2026-09-05", category_name="Alimentação")
        agent.add_transaction("IFOOD", 400, date="2026-09-25", category_name="Alimentação")  # depois do dia 20: fora
        agent.add_transaction("IFOOD", 300, date="2026-10-05", category_name="Alimentação")
        items = insights.month_insights(2026, 10, today=today)
        assert items[0]["kind"] == "category_increase"
        assert items[0]["category"] == "Alimentação"
        assert items[0]["amount"] == 200.0  # 300 contra 100 nos mesmos 20 dias
        assert "nos mesmos 20 dias de setembro" in items[0]["message"]

    def test_small_changes_are_ignored(self, agent):  # noqa: F811
        agent.add_transaction("IFOOD", 100, date="2026-09-05", category_name="Alimentação")
        agent.add_transaction("IFOOD", 130, date="2026-10-05", category_name="Alimentação")
        assert insights.month_insights(2026, 10, today=date(2026, 10, 20)) == []

    def test_budget_pace(self, agent):  # noqa: F811
        lazer = next(c for c in agent.list_categories() if c["name"] == "Lazer")
        agent.set_category_budget(lazer["id"], 300)
        agent.add_transaction("CINEMA", 250, date="2026-10-05", category_name="Lazer")
        items = insights.month_insights(2026, 10, today=date(2026, 10, 10))
        pace = next(i for i in items if i["kind"] == "budget_pace")
        assert pace["category"] == "Lazer"
        assert pace["amount"] == round(250 / 10 * 31 - 300, 2)

    def test_future_month_has_no_insights(self, agent):  # noqa: F811
        assert insights.month_insights(2026, 12, today=date(2026, 10, 20)) == []


# ── Bloqueio por PIN ────────────────────────────────────────────────────

class FakeConfig:
    def __init__(self):
        self.data = {}

    def get(self, *keys, default=None):
        cur = self.data
        for k in keys:
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur

    def set(self, value, *keys):
        cur = self.data
        for k in keys[:-1]:
            cur = cur.setdefault(k, {})
        cur[keys[-1]] = value


@pytest.fixture
def lock(monkeypatch):
    from desktop import lock as lock_mod

    monkeypatch.setattr(lock_mod, "config", FakeConfig())
    lock_mod._reset_for_tests()
    yield lock_mod
    lock_mod._reset_for_tests()


class TestLock:
    def test_no_pin_means_unlocked(self, lock):
        assert lock.status() == {"enabled": False, "locked": False, "timeout_minutes": 10, "retry_after_seconds": 0}

    def test_pin_is_hashed_and_unlocks(self, lock):
        lock.set_pin("1234")
        stored = lock.config.get("security", "pin_hash")
        assert stored.startswith("scrypt$") and "1234" not in stored
        lock.lock_now()
        assert lock.is_locked()
        with pytest.raises(lock.LockError):
            lock.unlock("0000")
        lock.unlock("1234")
        assert not lock.is_locked()

    def test_locks_again_after_idle(self, lock):
        lock.set_pin("1234")
        lock.set_timeout(5)
        lock.touch(now=1000.0)
        assert not lock.is_locked(now=1000.0 + 299)
        assert lock.is_locked(now=1000.0 + 301)

    def test_backoff_after_wrong_attempts(self, lock):
        lock.set_pin("1234")
        lock.lock_now()
        for _ in range(lock.FREE_ATTEMPTS + 1):
            with pytest.raises(lock.LockError):
                lock.unlock("9999", now=50.0)
        with pytest.raises(lock.LockError) as err:
            lock.unlock("1234", now=51.0)  # até o PIN certo espera
        assert err.value.status == 429
        lock.unlock("1234", now=60.0)

    def test_change_and_remove_need_current_pin(self, lock):
        lock.set_pin("1234")
        with pytest.raises(lock.LockError):
            lock.set_pin("5678", current_pin="0000")
        lock.set_pin("5678", current_pin="1234")
        with pytest.raises(lock.LockError):
            lock.set_pin("", current_pin="1234")
        lock.set_pin("", current_pin="5678")
        assert not lock.enabled()

    @pytest.mark.parametrize("pin", ["123", "123456789", "12a4", ""])
    def test_invalid_pin(self, lock, pin):
        if pin == "":
            return  # vazio = remover, coberto acima
        with pytest.raises(lock.LockError):
            lock.set_pin(pin)


def test_api_blocks_data_while_locked(temp_db, lock, monkeypatch):  # noqa: F811
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    import desktop.api as api

    monkeypatch.setattr(api, "migrate_plaintext_key", lambda cfg: False)
    lock.set_pin("2468")
    lock.lock_now()
    with TestClient(api.app, base_url="http://127.0.0.1") as c:
        assert c.get("/api/transactions").status_code == 423
        assert c.get("/api/boot").json()["lock"]["locked"] is True
        assert c.post("/api/lock/unlock", json={"pin": "1111"}).status_code == 401
        assert c.post("/api/lock/unlock", json={"pin": "2468"}).status_code == 200
        assert c.get("/api/transactions").status_code == 200
