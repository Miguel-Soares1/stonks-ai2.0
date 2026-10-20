"""Rotas de ajustes: provider/modelo de IA, bolsa padrão e informações do sistema."""

from typing import Any, Dict, List, Literal, Optional

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, Field

from desktop.state import financial_agent, reset_agents
from stonks_ai import __version__
from stonks_ai.config import DATA_DIR, config
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


class ThemeIn(BaseModel):
    theme: Literal["light", "dark", "system"]


@router.put("/settings/theme")
def save_theme(body: ThemeIn) -> Dict[str, str]:
    config.set(body.theme, "ui", "theme")
    return {"theme": body.theme}


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
        config.set(body.api_key.strip(), "llm", "api_key")
    config.set("ollama" if body.fallback_to_ollama else "", "llm", "fallback_provider")
    config.set(body.default_exchange, "stocks", "default_exchange")
    # Os agentes guardam o cliente LLM; recria para valer o novo provider/modelo
    reset_agents()
    return settings()


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
