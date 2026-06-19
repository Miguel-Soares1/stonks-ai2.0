"""
Provider LLM abstrato para o Stonks AI.

Define a interface comum para todos os providers de IA (local e remoto).
Suporta Ollama, OpenAI, DeepSeek, e qualquer API OpenAI-compatible.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger("stonks_ai.llm")


class LLMError(Exception):
    """Erro relacionado à comunicação com o modelo de IA."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class BaseLLMProvider(ABC):
    """Interface abstrata para providers de LLM."""

    def __init__(
        self,
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        timeout: int = 120,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self._available: Optional[bool] = None
        logger.debug(
            "%s initialized: model=%s, temperature=%s, max_tokens=%s, timeout=%s",
            self.__class__.__name__, model, temperature, max_tokens, timeout,
        )

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Gera texto a partir de um prompt."""

    @abstractmethod
    def generate_from_messages(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> str:
        """Gera texto a partir de uma lista de mensagens."""

    @abstractmethod
    def is_available(self) -> bool:
        """Verifica se o provider está disponível."""

    def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        output_format: str = "json",
    ) -> str:
        """Gera resposta estruturada (JSON) do modelo."""
        sys_prompt = system_prompt or ""
        if output_format == "json":
            sys_prompt += (
                "\n\nIMPORTANTE: Responda APENAS com JSON válido, "
                "sem markdown, sem texto adicional, sem formatação."
            )
        return self.generate(prompt, system_prompt=sys_prompt)

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Gera texto em streaming (token por token).

        Providers que suportam streaming devem sobrescrever este método.
        O fallback padrão gera tudo de uma vez como um único chunk.
        """
        result = self.generate(prompt, system_prompt=system_prompt)
        yield result

    @property
    def provider_name(self) -> str:
        """Nome descritivo do provider."""
        return self.__class__.__name__

    @property
    @abstractmethod
    def available_models(self) -> List[Dict[str, Any]]:
        """Lista modelos disponíveis no provider."""

    def validate_response(self, raw: str, expected_type: str = "text") -> str:
        """
        Valida e limpa uma resposta do modelo.

        Remove markdown fences, extrai JSON de blocos ```json, e sanitiza.
        """
        text = raw.strip()

        if expected_type == "json":
            # Remove markdown fences se existirem
            if text.startswith("```"):
                # Remove primeira linha (```json ou ```)
                lines = text.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                # Remove última linha se for ```
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                text = "\n".join(lines).strip()

        return text
