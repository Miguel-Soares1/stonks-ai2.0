"""
Provider OpenAI — API oficial platform.openai.com.

Modelos disponíveis:
- gpt-4o-mini — rápido, barato, ótimo para análise
- gpt-4o — melhor qualidade, mais caro
- gpt-4.1 — modelo mais recente (abril 2025)

Preço (aprox): ~$0.15/1M input tokens (gpt-4o-mini), ~$2.50/1M (gpt-4o)
"""

from typing import Optional

from stonks_ai.llm.openai_compatible_provider import OpenAICompatibleProvider

OPENAI_BASE_URL = "https://api.openai.com/v1"
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIProvider(OpenAICompatibleProvider):
    """Provider para a API oficial da OpenAI."""

    def __init__(
        self,
        api_key: str,
        model: str = OPENAI_DEFAULT_MODEL,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: int = 120,
    ):
        super().__init__(
            model=model,
            base_url=OPENAI_BASE_URL,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    @property
    def provider_name(self) -> str:
        return "OpenAI"
