"""Rotas de ajustes: provider/modelo de IA, bolsa padrão, backup e informações do sistema."""

import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from desktop import lock
from desktop.state import financial_agent, reset_agents
from stonks_ai import __version__, backup
from stonks_ai.config import DATA_DIR, config
from stonks_ai.credentials import store_api_key
from stonks_ai.database import db

router = APIRouter(prefix="/api")

Provider = Literal["ollama", "deepseek", "openai", "openai_compatible"]


class SettingsIn(BaseModel):
    provider: Provider
    model: str = Field(min_length=1, max_length=200)
    temperature: float = Field(ge=0, le=2)
    endpoint: str = Field(min_length=1, max_length=500)
    base_url: str = ""
    # None mantém a chave atual; "" apaga
    api_key: Optional[str] = None
    fallback_to_ollama: bool = True
    default_exchange: Literal["B3", "NYSE"] = "B3"


@router.get("/status")
def status() -> Dict[str, Any]:
    """Estado do sistema: provider de IA e onde os dados ficam."""
    return {
        "llm": {
            "available": financial_agent().check_llm_available(),
            "provider": config.get("llm", "provider", default="ollama"),
            "model": config.get("llm", "model", default=""),
        },
        "data_dir": str(DATA_DIR),
        "theme": config.get("ui", "theme", default="system"),
    }


@router.get("/boot")
def boot() -> Dict[str, Any]:
    """O mínimo para a primeira pintura da janela (rápido e liberado com o app bloqueado)."""
    return {
        "theme": config.get("ui", "theme", default="system"),
        "hide_values": bool(config.get("ui", "hide_values", default=False)),
        "lock": lock.status(),
    }


class ThemeIn(BaseModel):
    theme: Literal["light", "dark", "system"]


@router.put("/settings/theme")
def save_theme(body: ThemeIn) -> Dict[str, str]:
    config.set(body.theme, "ui", "theme")
    return {"theme": body.theme}


class HideValuesIn(BaseModel):
    hide_values: bool


@router.put("/settings/hide-values")
def save_hide_values(body: HideValuesIn) -> Dict[str, bool]:
    """Ocultar valores (R$ ••••) para usar o app perto de outras pessoas."""
    config.set(body.hide_values, "ui", "hide_values")
    return {"hide_values": body.hide_values}


@router.get("/settings")
def settings() -> Dict[str, Any]:
    llm = config.get("llm", default={}) or {}
    return {
        "provider": llm.get("provider", "ollama"),
        "model": llm.get("model", ""),
        "temperature": llm.get("temperature", 0.3),
        "endpoint": llm.get("endpoint", "http://localhost:11434"),
        "base_url": llm.get("base_url", ""),
        # A chave nunca volta para a interface; só se existe
        "has_api_key": bool(llm.get("api_key")),
        "fallback_to_ollama": llm.get("fallback_provider") == "ollama",
        "default_exchange": config.get("stocks", "default_exchange", default="B3"),
        "system": {
            "version": __version__,
            "data_dir": str(DATA_DIR),
            "database": str(db.db_path),
            "database_ok": db.health_check(),
        },
    }


@router.put("/settings")
def save_settings(body: SettingsIn) -> Dict[str, Any]:
    config.set(body.provider, "llm", "provider")
    config.set(body.model.strip(), "llm", "model")
    config.set(body.temperature, "llm", "temperature")
    config.set(body.endpoint.strip(), "llm", "endpoint")
    config.set(body.base_url.strip(), "llm", "base_url")
    if body.api_key is not None:
        # A chave vai para o Gerenciador de Credenciais do Windows; no config fica só um marcador
        config.set(store_api_key(body.api_key), "llm", "api_key")
    config.set("ollama" if body.fallback_to_ollama else "", "llm", "fallback_provider")
    config.set(body.default_exchange, "stocks", "default_exchange")
    # Os agentes guardam o cliente LLM; recria para valer o novo provider/modelo
    reset_agents()
    return settings()


# ── Bloqueio por PIN ────────────────────────────────────────────────────

class UnlockIn(BaseModel):
    pin: str = Field(max_length=32)


class PinIn(BaseModel):
    new_pin: str = Field(default="", max_length=32)  # vazio remove o PIN
    current_pin: str = Field(default="", max_length=32)


class LockTimeoutIn(BaseModel):
    minutes: int


def _lock_call(fn, *args) -> Dict[str, Any]:
    try:
        fn(*args)
    except lock.LockError as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    return lock.status()


@router.get("/lock")
def lock_status() -> Dict[str, Any]:
    return lock.status()


@router.post("/lock/unlock")
def lock_unlock(body: UnlockIn) -> Dict[str, Any]:
    return _lock_call(lock.unlock, body.pin)


@router.post("/lock/lock")
def lock_lock() -> Dict[str, Any]:
    return _lock_call(lock.lock_now)


@router.put("/lock/pin")
def lock_set_pin(body: PinIn) -> Dict[str, Any]:
    return _lock_call(lock.set_pin, body.new_pin, body.current_pin)


@router.put("/lock/timeout")
def lock_set_timeout(body: LockTimeoutIn) -> Dict[str, Any]:
    return _lock_call(lock.set_timeout, body.minutes)


# ── Backup ──────────────────────────────────────────────────────────────

MAX_RESTORE_BYTES = 500 * 1024 * 1024


@router.get("/backups")
def backups() -> Dict[str, Any]:
    return {"folder": str(backup.BACKUP_DIR), "items": backup.list_backups()}


@router.post("/backups", status_code=201)
def backup_create() -> Dict[str, Any]:
    try:
        return backup.create_backup()
    except backup.BackupError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/backups/{name}/restore")
def backup_restore(name: str) -> Dict[str, Any]:
    try:
        result = backup.restore_backup(backup.backup_path(name))
    except backup.BackupError as e:
        raise HTTPException(status_code=422, detail=str(e))
    reset_agents()
    return result


@router.post("/backups/restore-file")
async def backup_restore_file(request: Request) -> Dict[str, Any]:
    """Restaura a partir de um arquivo .db escolhido pelo usuário (o corpo é o arquivo)."""
    content = await request.body()
    if not content:
        raise HTTPException(status_code=422, detail="O arquivo está vazio.")
    if len(content) > MAX_RESTORE_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo maior que 500 MB.")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "restaurar.db"
        path.write_bytes(content)
        try:
            result = backup.restore_backup(path)
        except backup.BackupError as e:
            raise HTTPException(status_code=422, detail=str(e))
    reset_agents()
    return result


@router.post("/backups/open-folder", status_code=204)
def backup_open_folder() -> None:
    """Abre a pasta dos backups no Explorer, para copiar para um pendrive ou nuvem."""
    backup.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        os.startfile(backup.BACKUP_DIR)  # noqa: S606 — caminho fixo, não vem do usuário
    else:
        raise HTTPException(status_code=501, detail="Disponível só no Windows.")


@router.get("/settings/ollama-models")
def ollama_models() -> List[Dict[str, Any]]:
    """Modelos instalados no Ollama, com o tamanho em disco."""
    endpoint = config.get("llm", "endpoint", default="http://localhost:11434").rstrip("/")
    try:
        models = httpx.get(f"{endpoint}/api/tags", timeout=5).json().get("models", [])
    except Exception:
        return []
    return [
        {"name": m.get("name"), "size_gb": round(m.get("size", 0) / 1024**3, 2)}
        for m in sorted(models, key=lambda m: m.get("size", 0))
    ]
