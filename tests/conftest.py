"""Configuração comum dos testes."""

import pytest

from stonks_ai import backup
from stonks_ai.collectors.finance import categorizer
from stonks_ai.database import Database, db


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Todo teste usa um banco temporário: nenhum teste grava nos dados reais do usuário.

    Testes que precisam do banco já inicializado usam a fixture `temp_db`
    (tests/test_desktop_features.py), que troca este por outro já com as tabelas.
    """
    fresh = Database(tmp_path / "isolado.db")
    monkeypatch.setattr(db, "db_path", fresh.db_path)
    monkeypatch.setattr(db, "_engine", fresh._engine)
    monkeypatch.setattr(db, "_session_factory", fresh._session_factory)
    monkeypatch.setattr(backup, "BACKUP_DIR", tmp_path / "backups")
    db.initialize()
    categorizer.invalidate_cache()  # categorias e regras em cache são do banco anterior
    yield
    categorizer.invalidate_cache()
    fresh._engine.dispose()
