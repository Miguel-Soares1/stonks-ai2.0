"""
Integração com modelos de IA — local (Ollama) e remotos (DeepSeek, OpenAI, etc.).

Providers disponíveis:
- OllamaProvider: execução local via Ollama
- DeepSeekProvider: API deepseek.com (~$0.14/1M tokens)
- OpenAIProvider: API openai.com (GPT-4o-mini, GPT-4o)
- OpenAICompatibleProvider: qualquer API OpenAI-compatible

Uso:
    from stonks_ai.llm import create_llm_client
    llm = create_llm_client()  # usa config.yaml
    resposta = llm.generate("O que é P/L?")
"""

from stonks_ai.llm.base import BaseLLMProvider, LLMError
from stonks_ai.llm.ollama_provider import OllamaProvider
from stonks_ai.llm.deepseek_provider import DeepSeekProvider
from stonks_ai.llm.openai_provider import OpenAIProvider
from stonks_ai.llm.openai_compatible_provider import OpenAICompatibleProvider
from stonks_ai.llm.factory import FallbackChain, create_llm_client

# Backward compatibility: OllamaClient como alias de OllamaProvider
OllamaClient = OllamaProvider

__all__ = [
    "BaseLLMProvider",
    "LLMError",
    "OllamaProvider",
    "OllamaClient",  # deprecated, use OllamaProvider
    "DeepSeekProvider",
    "OpenAIProvider",
    "OpenAICompatibleProvider",
    "FallbackChain",
    "create_llm_client",
]
