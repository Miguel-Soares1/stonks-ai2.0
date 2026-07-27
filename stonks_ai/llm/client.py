"""
Compatibilidade retroativa — re-exporta do novo módulo de providers.

Este ficheiro é mantido para não quebrar imports existentes.
Novo código deve importar de stonks_ai.llm diretamente.
"""

from stonks_ai.llm.base import LLMError
from stonks_ai.llm.ollama_provider import OllamaProvider as OllamaClient
from stonks_ai.llm.factory import create_llm_client

# Instância global lazy — só é criada no primeiro acesso.
# Isto evita falhas no import quando o Ollama não está a correr.
_llm_client = None


def get_llm_client():
    """Retorna o cliente LLM global, criando-o lazy se necessário."""
    global _llm_client
    if _llm_client is None:
        from stonks_ai.config import config
        _llm_client = create_llm_client(config)
    return _llm_client


# Propriedade para compatibilidade: llm_client ainda funciona,
# mas agora é lazy (não falha no import).
class _LazyClient:
    def __getattr__(self, name):
        return getattr(get_llm_client(), name)

    def __repr__(self):
        return repr(get_llm_client())


llm_client = _LazyClient()

__all__ = ["LLMError", "OllamaClient", "llm_client", "create_llm_client", "get_llm_client"]
