"""
Cria o cliente da IA: sempre o Ollama, no computador do usuário.

As IAs na nuvem (DeepSeek, OpenAI) foram removidas (ADR 025): o projeto é gratuito e os dados
financeiros não saem do computador.
"""

import logging
import os
from typing import Optional

from stonks_ai.config import Config
from stonks_ai.llm.base import BaseLLMProvider
from stonks_ai.llm.ollama_provider import OllamaProvider

logger = logging.getLogger("stonks_ai.llm.factory")

DEFAULT_MODEL = "qwen2.5:3b"
DEFAULT_ENDPOINT = "http://localhost:11434"


def _resolve_env_var(value: str) -> str:
    """${VAR} ou ${VAR:-padrão} no config.yaml viram o valor da variável de ambiente."""
    if not isinstance(value, str) or not value.startswith("${"):
        return value
    inner = value[2:-1]
    var_name, _, default = inner.partition(":-")
    return os.environ.get(var_name.strip()) or default.strip()


def create_llm_client(config: Optional[Config] = None, temperature: Optional[float] = None) -> BaseLLMProvider:
    """Cliente do Ollama com o modelo, o endereço e os limites do config.yaml."""
    from stonks_ai.config import config as global_config

    cfg = config or global_config
    model = cfg.get("llm", "model", default=DEFAULT_MODEL)
    logger.info("Criando cliente Ollama: model=%s", model)
    return OllamaProvider(
        model=model,
        endpoint=_resolve_env_var(cfg.get("llm", "endpoint", default=DEFAULT_ENDPOINT)),
        temperature=cfg.get("llm", "temperature", default=0.3) if temperature is None else temperature,
        max_tokens=cfg.get("llm", "max_tokens", default=2048),
        timeout=cfg.get("llm", "timeout_seconds", default=120),
        num_ctx=cfg.get("llm", "num_ctx", default=4096),
        keep_alive=cfg.get("llm", "keep_alive", default="2m"),
    )
