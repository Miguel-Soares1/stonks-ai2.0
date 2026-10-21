"""Testes de transações recorrentes, backup e da chave da IA no cofre do sistema."""

import sqlite3
from datetime import date, timedelta

import pytest

from stonks_ai import backup
from stonks_ai.database import Database, db
from stonks_ai.models.transaction import Transaction
from stonks_ai.utils import recurrence


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Troca o banco global por um temporário (os dados reais não são tocados)."""
    fresh = Database(tmp_path / "test.db")
    monkeypatch.setattr(db, "db_path", fresh.db_path)
    monkeypatch.setattr(db, "_engine", fresh._engine)
    monkeypatch.setattr(db, "_session_factory", fresh._session_factory)
    monkeypatch.setattr(backup, "BACKUP_DIR", tmp_path / "backups")
    db.initialize()
    yield db
    fresh._engine.dispose()


@pytest.fixture
def agent(temp_db):
    from stonks_ai.agents.personal_finance_agent import PersonalFinanceAgent

    a = PersonalFinanceAgent()
    a.initialize()
    return a


def _series_dates(rid):
    with db.session() as s:
        rows = s.query(Transaction).filter(Transaction.recurrence_id == rid).order_by(Transaction.date).all()
        return [r.date.date() for r in rows]


# ── Recorrência: datas ──────────────────────────────────────────────────

class TestOccurrence:
    def test_monthly_keeps_day_31_when_possible(self):
        anchor = date(2026, 1, 31)
        assert recurrence.occurrence(anchor, "monthly", 1) == date(2026, 2, 28)
        assert recurrence.occurrence(anchor, "monthly", 2) == date(2026, 3, 31)

    def test_weekly_and_yearly(self):
        anchor = date(2024, 2, 29)
        assert recurrence.occurrence(anchor, "weekly", 2) == date(2024, 3, 14)
        assert recurrence.occurrence(anchor, "biweekly", 1) == date(2024, 3, 14)
        assert recurrence.occurrence(anchor, "yearly", 1) == date(2025, 2, 28)

    def test_invalid_frequency(self):
        with pytest.raises(ValueError):
            recurrence.occurrence(date(2026, 1, 1), "daily", 1)


# ── Recorrência: geração ────────────────────────────────────────────────

class TestRecurringTransactions:
    def test_series_started_in_past_catches_up_to_today(self, agent):
        start = date.today() - timedelta(weeks=3)
        tx = agent.add_transaction("Academia", 100, date=start.isoformat(), category_name="Saúde",
                                   recurring_frequency="weekly")
        assert tx["is_recurring"] is True
        with db.session() as s:
            rid = s.get(Transaction, tx["id"]).recurrence_id
        assert _series_dates(rid) == [start + timedelta(weeks=n) for n in range(4)]
        # Rodar de novo não duplica
        assert recurrence.generate_due() == 0

    def test_deleted_occurrence_is_not_recreated(self, agent):
        start = date.today() - timedelta(weeks=1)
        tx = agent.add_transaction("Aula", 50, date=start.isoformat(), recurring_frequency="weekly")
        with db.session() as s:
            rid = s.get(Transaction, tx["id"]).recurrence_id
            latest = s.query(Transaction).filter(Transaction.recurrence_id == rid).order_by(Transaction.date.desc()).first()
            latest_id = latest.id
        assert agent.delete_transaction(latest_id)
        assert recurrence.generate_due() == 0
        assert _series_dates(rid) == [start]

    def test_new_occurrence_uses_latest_values(self, agent, monkeypatch):
        start = date.today() - timedelta(weeks=1)
        tx = agent.add_transaction("Aluguel", 1500, date=start.isoformat(), recurring_frequency="weekly")
        with db.session() as s:
            rid = s.get(Transaction, tx["id"]).recurrence_id
            latest_id = s.query(Transaction).filter(Transaction.recurrence_id == rid).order_by(Transaction.date.desc()).first().id
        agent.update_transaction(latest_id, amount=1600, recurring_frequency="weekly")
        recurrence.generate_due(today=date.today() + timedelta(weeks=1))
        with db.session() as s:
            newest = s.query(Transaction).filter(Transaction.recurrence_id == rid).order_by(Transaction.date.desc()).first()
            assert newest.amount == 1600
            assert newest.source == "recurring"

    def test_stop_repeating(self, agent):
        start = date.today() - timedelta(days=1)
        tx = agent.add_transaction("Streaming", 40, date=start.isoformat(), recurring_frequency="monthly")
        updated = agent.update_transaction(tx["id"], recurring_frequency=None)
        assert updated["is_recurring"] is False
        assert recurrence.generate_due(today=date.today() + timedelta(days=400)) == 0
        assert recurrence.upcoming(days=400) == []

    def test_update_without_frequency_keeps_series(self, agent):
        tx = agent.add_transaction("Internet", 120, date=date.today().isoformat(), recurring_frequency="monthly")
        updated = agent.update_transaction(tx["id"], notes="fibra")
        assert updated["is_recurring"] is True
        assert updated["recurring_frequency"] == "monthly"

    def test_upcoming_lists_next_occurrence(self, agent):
        today = date.today()
        agent.add_transaction("Salário", 5000, date=today.isoformat(), tx_type="income", recurring_frequency="weekly")
        items = recurrence.upcoming(days=30)
        assert len(items) == 1
        assert items[0]["date"] == (today + timedelta(weeks=1)).isoformat()
        assert items[0]["type"] == "income"
        assert items[0]["frequency_label"] == "Toda semana"

    def test_catch_up_is_capped(self, agent):
        start = date.today() - timedelta(weeks=200)
        agent.add_transaction("Antiga", 1, date=start.isoformat(), recurring_frequency="weekly")
        with db.session() as s:
            count = s.query(Transaction).filter(Transaction.description == "Antiga").count()
        assert count == 1 + recurrence.MAX_CATCH_UP


# ── Backup ──────────────────────────────────────────────────────────────

class TestBackup:
    def test_create_list_and_restore(self, agent):
        agent.add_transaction("Antes do backup", 10)
        created = backup.create_backup()
        assert backup.list_backups()[0]["name"] == created["name"]

        agent.add_transaction("Depois do backup", 20)
        result = backup.restore_backup(backup.backup_path(created["name"]))
        descriptions = [t["description"] for t in agent.list_transactions(limit=50)]
        assert "Antes do backup" in descriptions
        assert "Depois do backup" not in descriptions
        # O estado anterior à restauração foi guardado
        assert result["safety_backup"].endswith("-antes.db")

    def test_rejects_path_traversal_and_unknown_names(self, temp_db):
        for name in ["../stonks_ai.db", "config.yaml", "stonks-20260101-000000.db"]:
            with pytest.raises(backup.BackupError):
                backup.backup_path(name)

    def test_rejects_file_that_is_not_a_stonks_database(self, temp_db, tmp_path):
        junk = tmp_path / "junk.db"
        junk.write_bytes(b"isto nao e um banco")
        with pytest.raises(backup.BackupError):
            backup.restore_backup(junk)

        other = tmp_path / "other.db"
        conn = sqlite3.connect(other)
        conn.execute("CREATE TABLE notas (id INTEGER)")
        conn.close()
        with pytest.raises(backup.BackupError):
            backup.restore_backup(other)

    def test_auto_backup_is_weekly_and_pruned(self, temp_db, monkeypatch):
        from datetime import datetime

        assert backup.auto_backup_if_due() is not None
        assert backup.auto_backup_if_due() is None  # já existe um desta semana

        # Simula 10 semanas de backups automáticos
        for week in range(10):
            stamp = (datetime(2020, 1, 1) + timedelta(weeks=week)).strftime("%Y%m%d-%H%M%S")
            (backup.BACKUP_DIR / f"stonks-{stamp}-auto.db").write_bytes(b"")
        monkeypatch.setattr(backup, "AUTO_INTERVAL", timedelta(0))
        backup.auto_backup_if_due()
        autos = [b for b in backup.list_backups() if b["reason"] == "auto"]
        assert len(autos) == backup.MAX_AUTO_BACKUPS


# ── IA só local (ADR 025) ───────────────────────────────────────────────

class TestOnlyLocalAI:
    def test_old_remote_config_goes_back_to_ollama(self, tmp_path):
        import yaml

        from stonks_ai.config import Config

        path = tmp_path / "config.yaml"
        path.write_text(yaml.safe_dump({"llm": {
            "provider": "deepseek", "model": "deepseek-chat", "api_key": "@keyring",
            "base_url": "", "fallback_provider": "ollama", "temperature": 0.5,
        }}), encoding="utf-8")
        cfg = Config(path)
        llm = cfg.get("llm")
        assert llm["model"] == "qwen2.5:3b"              # deepseek-chat não existe no Ollama
        assert llm["temperature"] == 0.5                  # o resto fica como estava
        assert not {"provider", "api_key", "base_url", "fallback_provider"} & set(llm)
        saved = yaml.safe_load(path.read_text(encoding="utf-8"))["llm"]
        assert "api_key" not in saved and "provider" not in saved

    def test_local_config_keeps_its_model(self, tmp_path):
        import yaml

        from stonks_ai.config import Config

        path = tmp_path / "config.yaml"
        path.write_text(yaml.safe_dump({"llm": {"provider": "ollama", "model": "qwen2.5:3b"}}), encoding="utf-8")
        assert Config(path).get("llm", "model") == "qwen2.5:3b"

    def test_client_is_always_ollama(self):
        from stonks_ai.llm import OllamaProvider, create_llm_client

        assert isinstance(create_llm_client(), OllamaProvider)
        assert create_llm_client(temperature=0.0).temperature == 0.0


# ── Logo ────────────────────────────────────────────────────────────────

def test_icon_file_has_every_size_and_matches_the_drawing(tmp_path):
    from PIL import Image

    from desktop import icon

    path = icon.write_ico(tmp_path / "stonks.ico")
    with Image.open(path) as ico:
        assert set(ico.info["sizes"]) == {(n, n) for n in icon.ICO_SIZES}
    # O .ico do repositório (usado no executável e no instalador) está gerado
    assert icon.ICON_PATH.exists()
    img = icon.image(32)
    assert img.getpixel((2, 16))[:3] == icon.BLUE[:3]        # fundo azul
    assert img.getpixel((0, 0))[3] == 0                        # canto arredondado transparente
