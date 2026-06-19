"""
Provider DeepSeek — API oficial deepseek.com (OpenAI-compatible).

Modelos disponíveis:
- deepseek-chat (V3) — melhor custo/benefício para chat e análise
- deepseek-reasoner (R1) — raciocínio avançado (mais lento, mais caro)

Preço (aprox): ~$0.14/1M input tokens, ~$0.28/1M output tokens
"""

from typing import Optional

from stonks_ai.llm.openai_compatible_provider import OpenAICompatibleProvider

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_DEFAULT_MODEL = "deepseek-chat"


class DeepSeekProvider(OpenAICompatibleProvider):
    """Provider para a API oficial do DeepSeek."""

    def __init__(
        self,
        api_key: str,
        model: str = DEEPSEEK_DEFAULT_MODEL,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: int = 120,
    ):
        super().__init__(
            model=model,
            base_url=DEEPSEEK_BASE_URL,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    @property
    def provider_name(self) -> str:
        return "DeepSeek"
