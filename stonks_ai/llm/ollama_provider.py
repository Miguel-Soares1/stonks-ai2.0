"""
Provider Ollama — execução local de LLMs.

Suporta qualquer modelo disponível no Ollama (llama3, mistral, gemma, etc.).
Implementa BaseLLMProvider com streaming nativo.
"""

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from stonks_ai.llm.base import BaseLLMProvider, LLMError

logger = logging.getLogger("stonks_ai.llm.ollama")


class OllamaProvider(BaseLLMProvider):
    """Provider para modelos locais via Ollama."""

    def __init__(
        self,
        model: str = "llama3.2:3b",
        endpoint: str = "http://localhost:11434",
        temperature: float = 0.3,
        max_tokens: int = 2048,
        timeout: int = 120,
    ):
        super().__init__(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        self.endpoint = endpoint
        self._available = False
        logger.debug(
            "OllamaProvider initialized: model=%s, endpoint=%s",
            self.model, self.endpoint,
        )

    def _check_ollama(self) -> None:
        """Verifica se o Ollama está a correr e o modelo está disponível."""
        try:
            import ollama

            logger.info("A verificar conexão com Ollama em: %s", self.endpoint)

            client = ollama.Client(host=self.endpoint)
            models_list = client.list()
            logger.info("Ollama conectado. Modelos disponíveis: %s", models_list)

            try:
                model_info = client.show(self.model)
                logger.info("Modelo '%s' encontrado: %s", self.model, model_info)
            except ollama.ResponseError as e:
                if "not found" in str(e).lower():
                    logger.error("Modelo '%s' não encontrado no Ollama", self.model)
                    raise LLMError(
                        "LLM-002",
                        f"Modelo '{self.model}' não encontrado. "
                        f"Baixe com: ollama pull {self.model}",
                    )
                logger.error("Erro ao verificar modelo '%s': %s", self.model, e)
                raise LLMError(
                    "LLM-004",
                    f"Erro ao verificar modelo '{self.model}': {e}",
                )

            self._available = True

        except ImportError:
            logger.error("Pacote 'ollama' não instalado")
            raise LLMError(
                "LLM-001",
                "Pacote 'ollama' não instalado. Execute: pip install ollama",
            )
        except ollama.ResponseError as e:
            error_msg = str(e).lower()
            logger.error("ResponseError do Ollama: %s", e)
            if any(
                keyword in error_msg
                for keyword in [
                    "connection", "connect", "refused", "econnrefused",
                    "econnreset", "timeout", "timed out",
                    "name or service not known", "cannot connect", "not found",
                ]
            ):
                raise LLMError(
                    "LLM-001",
                    "Ollama não está a correr. Inicie com 'ollama serve' "
                    "ou configure outro endpoint em config.yaml. "
                    "Baixe em: https://ollama.com/download",
                )
            raise LLMError("LLM-001", f"Erro na API Ollama: {e}")
        except Exception as e:
            logger.error("Erro ao conectar com Ollama: %s (type=%s)", e, type(e).__name__)
            error_type_name = f"{type(e).__module__}.{type(e).__name__}"
            error_msg = str(e).lower()
            if any(
                keyword in error_msg
                for keyword in [
                    "connection", "connect", "refused", "econnrefused",
                    "econnreset", "timeout", "timed out",
                    "name or service not known", "cannot connect",
                    "no address", "nodename nor servname",
                ]
            ):
                raise LLMError(
                    "LLM-001",
                    "Ollama não está a correr. Inicie com 'ollama serve' "
                    "ou configure outro endpoint em config.yaml. "
                    "Baixe em: https://ollama.com/download",
                )
            raise LLMError(
                "LLM-001",
                f"Erro ao conectar com Ollama ({error_type_name}): {e}",
            )

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
        self._check_ollama()

        try:
            import ollama

            full_messages = list(messages)
            if system_prompt:
                full_messages.insert(0, {"role": "system", "content": system_prompt})

            logger.debug(
                "Enviando chat para modelo '%s' (endpoint: %s, %d mensagens)",
                self.model, self.endpoint, len(full_messages),
            )
            client = ollama.Client(host=self.endpoint)
            response = client.chat(
                model=self.model,
                messages=full_messages,
                options={
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
            )

            result = response["message"]["content"]
            logger.debug("Resposta recebida (%d caracteres)", len(result))
            return result

        except ollama.ResponseError as e:
            if "out of memory" in str(e).lower() or "cuda" in str(e).lower():
                raise LLMError(
                    "LLM-003",
                    f"Memória insuficiente para rodar '{self.model}'. "
                    f"Tente um modelo menor como 'llama3.2:1b'",
                )
            raise LLMError("LLM-004", f"Erro na resposta do modelo: {e}")
        except Exception as e:
            raise LLMError("LLM-006", f"Erro ao gerar resposta: {e}")

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Streaming nativo via Ollama."""
        self._check_ollama()

        try:
            import ollama

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            logger.debug("Iniciando streaming para modelo '%s'", self.model)
            client = ollama.Client(host=self.endpoint)
            stream = client.chat(
                model=self.model,
                messages=messages,
                stream=True,
                options={
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
            )

            for chunk in stream:
                if "message" in chunk and "content" in chunk["message"]:
                    yield chunk["message"]["content"]

        except Exception as e:
            logger.error("Erro no streaming: %s", e)
            raise LLMError("LLM-006", f"Erro no streaming: {e}")

    # ── Health ────────────────────────────────────────────────────────

    def is_available(self) -> bool:
        if self._available:
            return True
        try:
            self._check_ollama()
            return True
        except LLMError:
            return False

    @property
    def available_models(self) -> List[Dict[str, Any]]:
        try:
            import ollama

            client = ollama.Client(host=self.endpoint)
            result = client.list()
            models = result.get("models", [])
            logger.debug("Modelos disponíveis no Ollama: %s", models)
            return models
        except Exception as e:
            logger.warning("Erro ao listar modelos Ollama: %s", e)
            return []
