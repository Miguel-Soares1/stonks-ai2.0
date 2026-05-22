"""
Cliente para integração com modelos de IA locais via Ollama.

Suporta qualquer modelo disponível no Ollama (llama3, mistral, gemma, etc.).
"""

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from stonks_ai.config import config

logger = logging.getLogger("stonks_ai.llm")


class LLMError(Exception):
    """Erro relacionado à comunicação com o modelo de IA local."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class OllamaClient:
    """Cliente para comunicação com o serviço Ollama local."""

    def __init__(
        self,
        model: Optional[str] = None,
        endpoint: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
    ):
        self.model = model or config.llm_model
        self.endpoint = endpoint or config.llm_endpoint
        self.temperature = temperature or config.get("llm", "temperature", default=0.3)
        self.max_tokens = max_tokens or config.get("llm", "max_tokens", default=2048)
        self.timeout = timeout or config.get("llm", "timeout_seconds", default=120)
        self._available = False
        logger.debug(
            "OllamaClient initialized: model=%s, endpoint=%s, temperature=%s, max_tokens=%s, timeout=%s",
            self.model, self.endpoint, self.temperature, self.max_tokens, self.timeout,
        )

    def _check_ollama(self) -> None:
        """Verifica se o Ollama está rodando e o modelo está disponível."""
        try:
            import ollama

            logger.info("Verificando conexão com Ollama em: %s", self.endpoint)

            # Cria cliente com o endpoint configurado (self.endpoint era ignorado!)
            client = ollama.Client(host=self.endpoint)

            # Verifica se o serviço está rodando
            logger.debug("Chamando client.list()...")
            models_list = client.list()
            logger.info("Ollama conectado. Modelos disponíveis: %s", models_list)

            # Verifica se o modelo específico está disponível
            logger.debug("Verificando modelo '%s'...", self.model)
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
            logger.info("Ollama disponível. Modelo: %s", self.model)

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
                    "connection",
                    "connect",
                    "refused",
                    "econnrefused",
                    "econnreset",
                    "timeout",
                    "timed out",
                    "name or service not known",
                    "cannot connect",
                    "not found",
                ]
            ):
                raise LLMError(
                    "LLM-001",
                    "Ollama não está rodando. Inicie com 'ollama serve' "
                    "ou configure outro endpoint em config.yaml. "
                    "Baixe em: https://ollama.com/download",
                )
            raise LLMError(
                "LLM-001",
                f"Erro na API Ollama: {e}",
            )
        except Exception as e:
            logger.error("Erro ao conectar com Ollama: %s (type=%s)", e, type(e).__name__)
            # httpx.ConnectError (não é subclasse de ConnectionError!)
            # Precisamos capturar explicitamente
            error_type_name = type(e).__module__ + "." + type(e).__name__
            error_msg = str(e).lower()
            if any(
                keyword in error_msg
                for keyword in [
                    "connection",
                    "connect",
                    "refused",
                    "econnrefused",
                    "econnreset",
                    "timeout",
                    "timed out",
                    "name or service not known",
                    "cannot connect",
                    "no address",
                    "nodename nor servname",
                ]
            ):
                raise LLMError(
                    "LLM-001",
                    "Ollama não está rodando. Inicie com 'ollama serve' "
                    "ou configure outro endpoint em config.yaml. "
                    "Baixe em: https://ollama.com/download",
                )
            raise LLMError(
                "LLM-001",
                f"Erro ao conectar com Ollama ({error_type_name}): {e}",
            )

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Gera texto a partir de um prompt usando o modelo local.

        Args:
            prompt: O prompt principal para o modelo.
            system_prompt: Prompt de sistema opcional para contextualizar.

        Returns:
            str: Texto gerado pelo modelo.

        Raises:
            LLMError: Se houver erro na comunicação com o modelo.
        """
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
        """
        Gera texto a partir de uma lista de mensagens usando o modelo local.

        Args:
            messages: Lista de mensagens no formato
                [{"role": "system"|"user"|"assistant", "content": "..."}].
            system_prompt: Prompt de sistema opcional (prepended às mensagens).

        Returns:
            str: Texto gerado pelo modelo.

        Raises:
            LLMError: Se houver erro na comunicação com o modelo.
        """
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

    def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        output_format: str = "json",
    ) -> str:
        """
        Gera resposta estruturada (JSON) do modelo.

        Args:
            prompt: O prompt para o modelo.
            system_prompt: Instruções de sistema adicionais.
            output_format: Formato esperado da saída (json, text).

        Returns:
            str: Resposta formatada do modelo.
        """
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

        Args:
            prompt: O prompt para o modelo.
            system_prompt: Prompt de sistema opcional.

        Yields:
            str: Fragmentos de texto conforme são gerados.
        """
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

    def is_available(self) -> bool:
        """Verifica se o Ollama e o modelo estão disponíveis."""
        if self._available:
            return True
        try:
            self._check_ollama()
            return True
        except LLMError:
            return False

    @property
    def available_models(self) -> List[Dict[str, Any]]:
        """Lista modelos disponíveis no Ollama."""
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


# Instância global configurada
llm_client = OllamaClient()
