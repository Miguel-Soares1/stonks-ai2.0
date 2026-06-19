"""
Compatibilidade retroativa — re-exporta do novo módulo de providers.

Este ficheiro é mantido para não quebrar imports existentes.
Novo código deve importar de stonks_ai.llm diretamente.
"""

from stonks_ai.llm.base import LLMError
from stonks_ai.llm.ollama_provider import OllamaProvider as OllamaClient
from stonks_ai.llm.factory import create_llm_client

# Instância global para compatibilidade (será deprecated)
# Novo código deve usar create_llm_client()
from stonks_ai.config import config

llm_client = create_llm_client(config)

__all__ = ["LLMError", "OllamaClient", "llm_client", "create_llm_client"]
