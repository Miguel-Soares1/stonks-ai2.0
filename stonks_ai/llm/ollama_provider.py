"""
Provider Ollama — execução local de LLMs.

Suporta qualquer modelo disponível no Ollama (llama3, mistral, gemma, etc.).
Implementa BaseLLMProvider com streaming nativo, retry automático e cache
de verificação de conectividade para evitar chamadas redundantes.
"""

import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from stonks_ai.llm.base import BaseLLMProvider, LLMError

logger = logging.getLogger("stonks_ai.llm.ollama")

# ── Constantes de retry ──────────────────────────────────────────────────
MAX_RETRIES = 3
BASE_DELAY = 1.0  # segundos (exponencial: 1s, 2s, 4s)
CHECK_TTL_SECONDS = 30  # cache da verificação de conectividade


def _is_connection_error(error: Exception) -> bool:
    """Determina se o erro é de conectividade (merece retry).

    Distingue entre erros de conexão (LLM-001) e erros de runtime do modelo
    (LLM-004, LLM-006). TimeoutError do Python não é tratado como conexão
    porque pode ser timeout de inferência, não de rede.
    """
    error_msg = str(error).lower()
    error_type = f"{type(error).__module__}.{type(error).__name__}".lower()

    # TimeoutError pode ser de inferência, não de conexão — não faz retry
    if "timeouterror" in error_type or "builtins.timeouterror" in error_type:
        return False

    # Keywords que indicam erro de conexão ou falha transitória
    connection_keywords = [
        "connection", "connect", "refused", "econnrefused",
        "econnreset",
        "name or service not known", "cannot connect",
        "no address", "nodename nor servname",
        "server disconnected", "broken pipe",
        "connection reset by peer", "connection refused",
        "http error", "503", "502", "504",  # HTTP server errors no Ollama
        "proxy error", "too many requests", "429",
    ]
    for kw in connection_keywords:
        if kw in error_msg or kw in error_type:
            return True
    return False


class OllamaProvider(BaseLLMProvider):
    """Provider para modelos locais via Ollama.

    Melhorias de resiliência (v0.1.1):
    - Cache de conectividade (TTL 30s) — evita chamadas redundantes
    - Timeout explícito no cliente HTTP
    - Retry com backoff exponencial (até 3 tentativas)
    - Pré-verificação TCP antes de chamar a API
    """

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
        self.endpoint = endpoint.rstrip("/")
        self._available = False
        self._last_check_time: float = 0.0
        self._last_check_success: bool = False
        logger.debug(
            "OllamaProvider initialized: model=%s, endpoint=%s, timeout=%ds",
            self.model, self.endpoint, self.timeout,
        )

    # ── Helpers de conectividade ─────────────────────────────────────────

    def _test_tcp_connect(self) -> bool:
        """Teste rápido de conectividade TCP (não bloqueia no handshake HTTP)."""
        import socket

        try:
            # Extrai host:port do endpoint
            url = self.endpoint
            if url.startswith("http://"):
                host_part = url[7:]
            elif url.startswith("https://"):
                host_part = url[8:]
            else:
                host_part = url

            if ":" in host_part:
                host, port_str = host_part.rsplit(":", 1)
                port = int(port_str)
            else:
                host = host_part
                port = 11434

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)  # timeout curto só para TCP
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception as e:
            logger.debug("TCP pre-check failed: %s", e)
            return False

    def _check_ollama(self, force: bool = False) -> None:
        """Verifica se o Ollama está a correr e o modelo está disponível.

        Usa cache com TTL para evitar chamadas redundantes em cada pedido.
        Passa force=True para ignorar o cache (ex: após timeout ou erro 5xx).
        """
        now = time.monotonic()
        cache_valid = (now - self._last_check_time) < CHECK_TTL_SECONDS

        if cache_valid and not force:
            if self._last_check_success:
                return
            # Se a última verificação falhou, tenta novamente após TTL
        if cache_valid and self._last_check_success and not force:
            return

        logger.debug("Verificando conectividade com Ollama (force=%s)...", force)

        # 1. Pré-verificação TCP (rápida, evita esperar timeout HTTP)
        if not self._test_tcp_connect():
            self._last_check_time = now
            self._last_check_success = False
            self._available = False
            raise LLMError(
                "LLM-001",
                "Ollama não está a correr. Inicie com 'ollama serve' "
                "ou configure outro endpoint em config.yaml. "
                "Baixe em: https://ollama.com/download",
            )

        # 2. Verificação completa via API
        try:
            import ollama

            logger.info("A verificar conexão com Ollama em: %s", self.endpoint)

            client = ollama.Client(host=self.endpoint, timeout=self.timeout)
            models_list = client.list()
            logger.debug("Ollama conectado. Modelos disponíveis: %s", models_list)

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
            self._last_check_time = now
            self._last_check_success = True

        except ImportError:
            logger.error("Pacote 'ollama' não instalado")
            raise LLMError(
                "LLM-001",
                "Pacote 'ollama' não instalado. Execute: pip install ollama",
            )
        except ollama.ResponseError as e:
            error_msg = str(e).lower()
            logger.error("ResponseError do Ollama: %s", e)
            self._last_check_time = now
            self._last_check_success = False
            self._available = False
            if _is_connection_error(e):
                raise LLMError(
                    "LLM-001",
                    "Ollama não está a correr. Inicie com 'ollama serve' "
                    "ou configure outro endpoint em config.yaml. "
                    "Baixe em: https://ollama.com/download",
                )
            raise LLMError("LLM-001", f"Erro na API Ollama: {e}")
        except Exception as e:
            logger.error("Erro ao conectar com Ollama: %s (type=%s)", e, type(e).__name__)
            self._last_check_time = now
            self._last_check_success = False
            self._available = False
            error_type_name = f"{type(e).__module__}.{type(e).__name__}"
            if _is_connection_error(e):
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

    def _ensure_available(self) -> None:
        """Garante conectividade, usando cache para evitar verificações redundantes."""
        if self._available:
            # Já verificado com sucesso dentro do TTL
            return
        self._check_ollama()

    # ── Retry logic ──────────────────────────────────────────────────────

    def _call_with_retry(self, func, *args, **kwargs) -> Any:
        """Executa uma função com retry automático em falhas de conexão.

        Usa backoff exponencial: 1s, 2s, 4s.
        Em caso de falha de conexão, força re-verificação da conectividade.
        """
        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return func(*args, **kwargs)
            except (LLMError, Exception) as e:
                last_error = e

                # Só faz retry em erros de conectividade
                if isinstance(e, LLMError):
                    is_conn = e.code in ("LLM-001", "LLM-007")
                else:
                    is_conn = _is_connection_error(e)

                if not is_conn or attempt == MAX_RETRIES:
                    raise

                delay = BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "Tentativa %d/%d falhou (%s). Retry em %.1fs...",
                    attempt, MAX_RETRIES, e, delay,
                )
                time.sleep(delay)

                # Força re-verificação após falha de conexão
                self._available = False
                self._last_check_success = False

        # Não deveria chegar aqui, mas segurança
        raise last_error  # type: ignore[misc]

    # ── Core Interface ───────────────────────────────────────────────────

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
        return self._call_with_retry(
            self._do_generate_from_messages, messages, system_prompt,
        )

    def _do_generate_from_messages(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> str:
        """Implementação real de generate_from_messages (sem retry)."""
        self._ensure_available()

        try:
            import ollama

            full_messages = list(messages)
            if system_prompt:
                full_messages.insert(0, {"role": "system", "content": system_prompt})

            logger.debug(
                "Enviando chat para modelo '%s' (endpoint: %s, %d mensagens)",
                self.model, self.endpoint, len(full_messages),
            )
            client = ollama.Client(host=self.endpoint, timeout=self.timeout)
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
            err_msg = str(e).lower()
            if "out of memory" in err_msg or "cuda" in err_msg:
                raise LLMError(
                    "LLM-003",
                    f"Memória insuficiente para rodar '{self.model}'. "
                    f"Tente um modelo menor como 'llama3.2:1b'",
                )
            if _is_connection_error(e):
                self._available = False
                self._last_check_success = False
                raise LLMError(
                    "LLM-001",
                    f"Conexão perdida com Ollama: {e}",
                )
            raise LLMError("LLM-004", f"Erro na resposta do modelo: {e}")
        except Exception as e:
            if _is_connection_error(e):
                self._available = False
                self._last_check_success = False
                raise LLMError("LLM-001", f"Conexão perdida com Ollama: {e}")
            raise LLMError("LLM-006", f"Erro ao gerar resposta: {e}")

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Streaming nativo via Ollama."""
        self._ensure_available()

        try:
            import ollama

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            logger.debug("Iniciando streaming para modelo '%s'", self.model)
            client = ollama.Client(host=self.endpoint, timeout=self.timeout)
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
            if _is_connection_error(e):
                self._available = False
                self._last_check_success = False
            raise LLMError("LLM-006", f"Erro no streaming: {e}")

    # ── Health ───────────────────────────────────────────────────────────

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

            client = ollama.Client(host=self.endpoint, timeout=self.timeout)
            result = client.list()
            models = result.get("models", [])
            logger.debug("Modelos disponíveis no Ollama: %s", models)
            return models
        except Exception as e:
            logger.warning("Erro ao listar modelos Ollama: %s", e)
            return []
