"""
Provider base para APIs OpenAI-compatible (OpenAI, DeepSeek, OpenRouter, etc.).

Implementa BaseLLMProvider usando httpx para chamadas REST.
Suporta streaming via Server-Sent Events (SSE).
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from stonks_ai.llm.base import BaseLLMProvider, LLMError

logger = logging.getLogger("stonks_ai.llm.openai_compat")

# Timeout padrão para chamadas à API
DEFAULT_TIMEOUT = httpx.Timeout(120.0, connect=15.0)


class OpenAICompatibleProvider(BaseLLMProvider):
    """
    Provider genérico para qualquer API OpenAI-compatible.

    Usado como base para OpenAIProvider e DeepSeekProvider.
    Também pode ser usado diretamente para OpenRouter, Groq, etc.
    """

    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        timeout: int = 120,
        extra_headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._http_client: Optional[httpx.Client] = None
        self._extra_headers = extra_headers or {}

    @property
    def http_client(self) -> httpx.Client:
        """Cliente HTTP lazy com headers de autenticação."""
        if self._http_client is None:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                **self._extra_headers,
            }
            self._http_client = httpx.Client(
                base_url=self.base_url,
                headers=headers,
                timeout=DEFAULT_TIMEOUT,
            )
        return self._http_client

    # ── Core Interface ────────────────────────────────────────────────

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self.generate_from_messages(messages)

    def generate_from_messages(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> str:
        full_messages = list(messages)
        if system_prompt:
            full_messages.insert(0, {"role": "system", "content": system_prompt})

        payload = {
            "model": self.model,
            "messages": full_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        try:
            logger.debug(
                "Chamando %s/chat/completions (model=%s, %d mensagens)",
                self.base_url, self.model, len(full_messages),
            )
            response = self.http_client.post(
                "/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]
            logger.debug("Resposta recebida (%d caracteres)", len(content))
            return content

        except httpx.HTTPStatusError as e:
            return self._handle_http_error(e)
        except httpx.TimeoutException:
            raise LLMError(
                "LLM-007",
                f"Timeout ao contactar {self.__class__.__name__} "
                f"({self.timeout}s). Tente novamente.",
            )
        except httpx.RequestError as e:
            raise LLMError(
                "LLM-007",
                f"Erro de rede ao contactar {self.__class__.__name__}: {e}",
            )
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise LLMError(
                "LLM-004",
                f"Resposta inesperada da API ({self.__class__.__name__}): {e}",
            )

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Streaming via SSE (Server-Sent Events)."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=DEFAULT_TIMEOUT,
            ) as client:
                async with client.stream(
                    "POST",
                    "/chat/completions",
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                            except (json.JSONDecodeError, KeyError, IndexError):
                                continue

        except httpx.HTTPStatusError as e:
            raise LLMError("LLM-007", self._build_http_error_message(e))
        except httpx.TimeoutException:
            raise LLMError(
                "LLM-007",
                f"Timeout no streaming ({self.__class__.__name__}). Tente novamente.",
            )
        except Exception as e:
            raise LLMError("LLM-006", f"Erro no streaming: {e}")

    # ── Health ────────────────────────────────────────────────────────

    def is_available(self) -> bool:
        """Verifica conectividade listando modelos disponíveis."""
        try:
            response = self.http_client.get("/models")
            response.raise_for_status()
            self._available = True
            return True
        except Exception as e:
            logger.warning("%s indisponível: %s", self.__class__.__name__, e)
            self._available = False
            return False

    @property
    def available_models(self) -> List[Dict[str, Any]]:
        """Lista modelos disponíveis na API."""
        try:
            response = self.http_client.get("/models")
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            logger.warning("Erro ao listar modelos de %s: %s", self.__class__.__name__, e)
            return []

    # ── Error Handling ────────────────────────────────────────────────

    def _handle_http_error(self, error: httpx.HTTPStatusError) -> None:
        """Trata erros HTTP da API."""
        status = error.response.status_code

        if status == 401:
            raise LLMError(
                "LLM-005",
                f"API Key inválida para {self.__class__.__name__}. "
                f"Verifique a configuração em config.yaml.",
            )
        elif status == 402 or status == 429:
            raise LLMError(
                "LLM-008",
                f"Limite de quota ou créditos excedidos em {self.__class__.__name__}. "
                f"Verifique o seu plano ou aguarde.",
            )
        elif status >= 500:
            raise LLMError(
                "LLM-007",
                f"Erro do servidor {self.__class__.__name__} (HTTP {status}). "
                f"Tente novamente em alguns segundos.",
            )
        else:
            error_body = ""
            try:
                error_body = error.response.json()
            except Exception:
                error_body = error.response.text[:500]
            raise LLMError(
                "LLM-007",
                f"Erro HTTP {status} em {self.__class__.__name__}: {error_body}",
            )

    @staticmethod
    def _build_http_error_message(error: httpx.HTTPStatusError) -> str:
        """Constrói mensagem de erro amigável."""
        status = error.response.status_code
        try:
            body = error.response.json()
            if "error" in body:
                msg = body["error"].get("message", str(body))
                return f"HTTP {status}: {msg}"
        except Exception:
            pass
        return f"HTTP {status}: {error.response.text[:300]}"
