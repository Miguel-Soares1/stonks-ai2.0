"""
Gerenciamento do banco de dados SQLite via SQLAlchemy.

Gerencia conexão, sessões, migrações e operações básicas de CRUD.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.exc import DatabaseError as SA_DatabaseError, OperationalError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from stonks_ai.config import config

# Schema version for migration tracking
SCHEMA_VERSION = 1


class Base(DeclarativeBase):
    """Classe base declarativa para todos os modelos ORM."""

    pass


class DatabaseError(Exception):
    """Erro relacionado ao banco de dados."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class Database:
    """Gerenciador de conexão e operações do banco SQLite."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.db_path
        self._engine = None
        self._session_factory = None
        self._connect()

    def _connect(self) -> None:
        """Estabelece conexão com o banco SQLite."""
        try:
            # Garante que o diretório existe
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # E028: Verifica espaço em disco
            self._check_disk_space()

            # Cria engine SQLAlchemy
            db_url = f"sqlite:///{self.db_path}"
            self._engine = create_engine(
                db_url,
                echo=False,
                connect_args={"check_same_thread": False},
            )

            # Configura SQLite para WAL mode (melhor performance concorrente)
            # Usar event.listen em vez de decorator para evitar registros duplicados
            # se _connect() for chamado novamente
            def _set_sqlite_pragma(dbapi_connection, connection_record):
                if isinstance(dbapi_connection, sqlite3.Connection):
                    cursor = dbapi_connection.cursor()
                    cursor.execute("PRAGMA journal_mode=WAL")
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.execute("PRAGMA busy_timeout=5000")
                    cursor.close()

            event.listen(self._engine, "connect", _set_sqlite_pragma)

            self._session_factory = sessionmaker(
                bind=self._engine,
                expire_on_commit=False,
            )

        except DatabaseError:
            raise
        except SA_DatabaseError as e:
            # E026: Banco corrompido ou problema de integridade
            err_str = str(e).lower()
            if "database disk image is malformed" in err_str or "file is not a database" in err_str:
                raise DatabaseError(
                    "DB-001",
                    f"Banco de dados corrompido. Execute 'stonks db repair' "
                    f"ou delete {self.db_path}",
                )
            raise DatabaseError(
                "DB-003",
                f"Erro de banco de dados: {e}",
            )
        except Exception as e:
            raise DatabaseError(
                "DB-003",
                f"Falha ao conectar ao banco de dados: {e}",
            )

    def _check_disk_space(self) -> None:
        """E028: Verifica se há espaço em disco suficiente."""
        try:
            if self.db_path.exists():
                # Verifica espaço no filesystem
                stat = self.db_path.stat()
                # No Windows, usamos shutil para verificar espaço
                import shutil
                usage = shutil.disk_usage(self.db_path.parent)
                # Menos de 10MB livres
                if usage.free < 10 * 1024 * 1024:
                    raise DatabaseError(
                        "DB-003",
                        "Sem espaço em disco para salvar dados. "
                        "Libere espaço ou mude DATA_DIR.",
                    )
        except DatabaseError:
            raise
        except Exception:
            # Falha na verificação não deve impedir conexão
            pass

    def _check_schema_version(self) -> None:
        """E027: Verifica se o schema do banco está atualizado."""
        try:
            if not self.db_path.exists():
                return

            inspector = inspect(self._engine)
            tables = inspector.get_table_names()

            if not tables:
                return

            # Tenta ler versão do schema de uma tabela de metadados
            with self.session() as s:
                try:
                    result = s.execute(
                        text(
                            "SELECT value FROM user_preferences "
                            "WHERE key = 'schema_version'"
                        )
                    ).scalar()
                except Exception:
                    # Tabela user_preferences pode não existir ainda
                    result = None

            if result is not None:
                db_version = int(result)
                if db_version < SCHEMA_VERSION:
                    raise DatabaseError(
                        "DB-002",
                        f"Schema do banco desatualizado (v{db_version} -> v{SCHEMA_VERSION}). "
                        f"Execute 'stonks init' para migrar.",
                    )
            else:
                # Primeira execução ou sem metadados - versão é 1 após criação
                pass

        except DatabaseError:
            raise
        except Exception:
            # Se falhar, não bloqueia inicialização
            pass

    def initialize(self) -> None:
        """Cria todas as tabelas definidas nos modelos ORM."""
        try:
            from stonks_ai.models import __all_models__  # noqa: F401

            # E026: Detecta corrupção antes de criar tabelas
            if self.db_path.exists():
                try:
                    with self.session() as s:
                        s.execute(text("SELECT COUNT(*) FROM sqlite_master"))
                except (SA_DatabaseError, OperationalError) as e:
                    err_str = str(e).lower()
                    if "database disk image is malformed" in err_str or "file is not a database" in err_str:
                        raise DatabaseError(
                            "DB-001",
                            f"Banco de dados corrompido. Execute 'stonks db repair' "
                            f"ou delete {self.db_path}",
                        )
                    raise

            Base.metadata.create_all(self._engine)

            # Salva versão do schema após criar tabelas
            try:
                with self.session() as s:
                    s.execute(
                        text(
                            "INSERT OR REPLACE INTO user_preferences "
                            "(key, value) VALUES ('schema_version', :ver)"
                        ),
                        {"ver": str(SCHEMA_VERSION)},
                    )
            except Exception:
                pass

            # Verifica se schema está atualizado
            self._check_schema_version()

        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(
                "DB-002",
                f"Erro ao inicializar schema do banco: {e}",
            )

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Context manager para sessão do banco com rollback automático em erro."""
        if self._session_factory is None:
            raise DatabaseError("DB-001", "Banco de dados não inicializado.")

        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def health_check(self) -> bool:
        """Verifica se o banco está acessível."""
        try:
            with self.session() as s:
                s.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    @property
    def engine(self):
        return self._engine


# Singleton global
db = Database()
