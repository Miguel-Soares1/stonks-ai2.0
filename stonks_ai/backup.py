"""
Backup e restauração do banco SQLite.

Usa a API de backup do próprio SQLite, que copia o banco com segurança mesmo com o
app aberto (modo WAL). As cópias ficam em DATA_DIR/backups com o nome
stonks-AAAAMMDD-HHMMSS[-motivo].db; as automáticas são semanais e só as últimas
MAX_AUTO_BACKUPS são mantidas.
"""

import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from stonks_ai.config import DATA_DIR
from stonks_ai.database import db

BACKUP_DIR = DATA_DIR / "backups"
NAME_RE = re.compile(r"^stonks-\d{8}-\d{6}(-[a-z]+)?\.db$")
AUTO_REASON = "auto"
AUTO_INTERVAL = timedelta(days=7)
MAX_AUTO_BACKUPS = 8

# Sem estas tabelas o arquivo não é um banco do Stonks AI
REQUIRED_TABLES = {"transactions", "categories"}


class BackupError(Exception):
    """Erro ao criar ou restaurar um backup."""


def _copy(src: Path, dest: Path) -> None:
    source = sqlite3.connect(src)
    target = sqlite3.connect(dest)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()


def create_backup(reason: str = "") -> Dict[str, Any]:
    """Cria uma cópia do banco atual e devolve os dados dela."""
    if not db.db_path.exists():
        raise BackupError("Ainda não há dados para copiar.")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = BACKUP_DIR / f"stonks-{stamp}{f'-{reason}' if reason else ''}.db"
    _copy(db.db_path, dest)
    return _info(dest)


def list_backups() -> List[Dict[str, Any]]:
    """Backups existentes, do mais novo ao mais antigo."""
    if not BACKUP_DIR.exists():
        return []
    files = [p for p in BACKUP_DIR.iterdir() if p.is_file() and NAME_RE.match(p.name)]
    return [_info(p) for p in sorted(files, key=lambda p: p.name, reverse=True)]


def _info(path: Path) -> Dict[str, Any]:
    m = re.match(r"^stonks-(\d{8}-\d{6})(?:-([a-z]+))?\.db$", path.name)
    created = datetime.strptime(m.group(1), "%Y%m%d-%H%M%S") if m else None
    return {
        "name": path.name,
        "created_at": created.isoformat() if created else None,
        "reason": (m.group(2) if m else None) or "manual",
        "size_bytes": path.stat().st_size,
    }


def backup_path(name: str) -> Path:
    """Caminho de um backup pelo nome, sem permitir sair da pasta de backups."""
    if not NAME_RE.match(name):
        raise BackupError("Nome de backup inválido.")
    path = BACKUP_DIR / name
    if not path.is_file():
        raise BackupError("Backup não encontrado.")
    return path


def validate_backup_file(path: Path) -> None:
    """Confere se o arquivo é um banco SQLite íntegro do Stonks AI."""
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise BackupError("O arquivo está corrompido.")
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            conn.close()
    except sqlite3.DatabaseError:
        raise BackupError("O arquivo não é um backup do Stonks AI.")
    if not REQUIRED_TABLES <= tables:
        raise BackupError("O arquivo não é um backup do Stonks AI.")


def restore_backup(path: Path) -> Dict[str, Any]:
    """
    Substitui os dados atuais pelos do backup.

    Antes, salva uma cópia do estado atual (motivo "antes"), para dar para desfazer.
    """
    validate_backup_file(path)
    safety: Optional[Dict[str, Any]] = None
    if db.db_path.exists():
        safety = create_backup("antes")
    # Fecha as conexões abertas pelo app antes de sobrescrever o banco
    db.engine.dispose()
    _copy(path, db.db_path)
    db.engine.dispose()
    db.initialize()  # cria tabelas que um backup antigo não tenha
    return {"restored": path.name, "safety_backup": safety["name"] if safety else None}


def auto_backup_if_due(now: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
    """Faz o backup semanal se o último automático tiver mais de 7 dias. Mantém só os últimos."""
    now = now or datetime.now()
    autos = [b for b in list_backups() if b["reason"] == AUTO_REASON]
    if autos and now - datetime.fromisoformat(autos[0]["created_at"]) < AUTO_INTERVAL:
        return None
    if not db.db_path.exists():
        return None
    created = create_backup(AUTO_REASON)
    for old in [b for b in list_backups() if b["reason"] == AUTO_REASON][MAX_AUTO_BACKUPS:]:
        (BACKUP_DIR / old["name"]).unlink(missing_ok=True)
    return created
