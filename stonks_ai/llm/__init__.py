"""
IA do Stonks AI: modelos locais pelo Ollama, no computador do usuário (ADR 025).

Uso:
    from stonks_ai.llm import create_llm_client
    llm = create_llm_client()  # usa config.yaml
    resposta = llm.generate("O que é P/L?")
"""

from stonks_ai.llm.base import BaseLLMProvider, LLMError
from stonks_ai.llm.ollama_provider import OllamaProvider
from stonks_ai.llm.factory import create_llm_client

# Backward compatibility: OllamaClient como alias de OllamaProvider
OllamaClient = OllamaProvider

__all__ = [
    "BaseLLMProvider",
    "LLMError",
    "OllamaProvider",
    "OllamaClient",  # deprecated, use OllamaProvider
    "create_llm_client",
]
