"""
Factory de providers LLM com fallback chain automático.

Cria o provider apropriado baseado na configuração e gere fallback
entre providers remotos e locais quando ocorrem falhas.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from stonks_ai.config import Config
from stonks_ai.llm.base import BaseLLMProvider, LLMError
from stonks_ai.llm.ollama_provider import OllamaProvider
from stonks_ai.llm.deepseek_provider import DeepSeekProvider
from stonks_ai.llm.openai_provider import OpenAIProvider
from stonks_ai.llm.openai_compatible_provider import OpenAICompatibleProvider

logger = logging.getLogger("stonks_ai.llm.factory")

# Mapeamento provider_type → classe
PROVIDER_REGISTRY = {
    "ollama": OllamaProvider,
    "deepseek": DeepSeekProvider,
    "openai": OpenAIProvider,
    "openai_compatible": OpenAICompatibleProvider,
}


def _resolve_env_var(value: str) -> str:
    """
    Resolve variáveis de ambiente em strings de configuração.

    Suporta os formatos:
    - ${VAR_NAME} → valor da variável de ambiente ou Streamlit Secret
    - ${VAR_NAME:-default} → valor da variável ou fallback
    - texto puro → retorna como está
    """
    if not isinstance(value, str) or not value.startswith("${"):
        return value

    # Remove ${ e }
    inner = value[2:-1]

    if ":-" in inner:
        var_name, default = inner.split(":-", 1)
        var_name = var_name.strip()
        default = default.strip()
    else:
        var_name = inner.strip()
        default = ""

    # 1. Tenta os.environ
    env_value = os.environ.get(var_name)
    if env_value:
        return env_value

    # 2. Tenta st.secrets (Streamlit Cloud)
    try:
        import streamlit as st
        secret_value = st.secrets.get(var_name)
        if secret_value:
            return secret_value
    except Exception:
        pass

    return default


def create_llm_client(config: Optional[Config] = None) -> BaseLLMProvider:
    """
    Cria o cliente LLM apropriado com base na configuração.

    Args:
        config: Instância de Config. Se None, usa o singleton global.

    Returns:
        BaseLLMProvider configurado e pronto para uso.

    Raises:
        LLMError: Se nenhum provider puder ser criado.
    """
    from stonks_ai.config import config as global_config

    cfg = config or global_config

    provider_type = cfg.get("llm", "provider", default="ollama")
    model = cfg.get("llm", "model", default="llama3.2:3b")
    temperature = cfg.get("llm", "temperature", default=0.3)
    max_tokens = cfg.get("llm", "max_tokens", default=2048)
    timeout = cfg.get("llm", "timeout_seconds", default=120)

    # Resolve API key (suporta env vars)
    raw_api_key = cfg.get("llm", "api_key", default="")
    api_key = _resolve_env_var(raw_api_key)

    # Resolve base_url
    raw_base_url = cfg.get("llm", "base_url", default="")
    base_url = _resolve_env_var(raw_base_url)

    # Fallback provider (para chain de resiliência)
    fallback_provider = cfg.get("llm", "fallback_provider", default="ollama")

    logger.info(
        "Criando provider LLM: type=%s, model=%s, fallback=%s",
        provider_type, model, fallback_provider,
    )

    primary = _create_provider(
        provider_type=provider_type,
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        config=cfg,
    )

    if primary is None:
        logger.warning(
            "Provider primário '%s' não pôde ser criado. A tentar fallback '%s'.",
            provider_type, fallback_provider,
        )
        return _create_fallback(cfg, fallback_provider)

    # Se o provider primário é remoto, envolvemos em FallbackChain
    if provider_type != "ollama" and fallback_provider:
        fallback = _create_fallback(cfg, fallback_provider)
        if fallback:
            return FallbackChain(primary=primary, fallback=fallback)
        logger.warning(
            "Fallback provider '%s' não disponível. Usando apenas provider primário.",
            fallback_provider,
        )

    return primary


def _create_provider(
    provider_type: str,
    model: str,
    api_key: str,
    base_url: str,
    temperature: float,
    max_tokens: int,
    timeout: int,
    config: Config,
) -> Optional[BaseLLMProvider]:
    """Cria uma instância de provider específico."""

    try:
        if provider_type == "ollama":
            endpoint = config.get("llm", "endpoint", default="http://localhost:11434")
            return OllamaProvider(
                model=model,
                endpoint=endpoint,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )

        elif provider_type == "deepseek":
            if not api_key:
                logger.error("DeepSeek requer api_key. Defina em config.yaml ou variável de ambiente.")
                return None
            return DeepSeekProvider(
                api_key=api_key,
                model=model or "deepseek-chat",
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )

        elif provider_type == "openai":
            if not api_key:
                logger.error("OpenAI requer api_key. Defina em config.yaml ou variável de ambiente.")
                return None
            return OpenAIProvider(
                api_key=api_key,
                model=model or "gpt-4o-mini",
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )

        elif provider_type == "openai_compatible":
            if not api_key:
                logger.error("Provider openai_compatible requer api_key.")
                return None
            resolved_base_url = base_url or "https://api.openai.com/v1"
            return OpenAICompatibleProvider(
                model=model,
                base_url=resolved_base_url,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )

        else:
            logger.error("Provider desconhecido: '%s'. Providers disponíveis: %s",
                         provider_type, list(PROVIDER_REGISTRY.keys()))
            return None

    except Exception as e:
        logger.error("Erro ao criar provider '%s': %s", provider_type, e)
        return None


def _create_fallback(config: Config, fallback_type: str) -> Optional[BaseLLMProvider]:
    """Cria o provider de fallback."""
    if fallback_type == "ollama":
        try:
            model = config.get("llm", "model", default="llama3.2:3b")
            endpoint = config.get("llm", "endpoint", default="http://localhost:11434")
            return OllamaProvider(
                model=model,
                endpoint=endpoint,
                temperature=config.get("llm", "temperature", default=0.3),
                max_tokens=config.get("llm", "max_tokens", default=2048),
                timeout=config.get("llm", "timeout_seconds", default=120),
            )
        except Exception as e:
            logger.warning("Fallback Ollama indisponível: %s", e)
            return None
    return None


class FallbackChain(BaseLLMProvider):
    """
    Provider com fallback automático.

    Tenta o provider primário primeiro. Se falhar, tenta o fallback.
    Implementa a interface BaseLLMProvider completa.
    """

    def __init__(self, primary: BaseLLMProvider, fallback: BaseLLMProvider):
        super().__init__(
            model=primary.model,
            temperature=primary.temperature,
            max_tokens=primary.max_tokens,
            timeout=primary.timeout,
        )
        self._primary = primary
        self._fallback = fallback
        self._using_fallback = False

    def _try_primary_first(self, method_name: str, *args, **kwargs) -> Any:
        """Tenta executar no primário, cai no fallback se falhar."""
        try:
            if not self._using_fallback:
                result = getattr(self._primary, method_name)(*args, **kwargs)
                return result
        except (LLMError, Exception) as e:
            logger.warning(
                "Provider primário (%s) falhou: %s. A usar fallback (%s).",
                self._primary.provider_name, e, self._fallback.provider_name,
            )
            self._using_fallback = True

        return getattr(self._fallback, method_name)(*args, **kwargs)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        return self._try_primary_first("generate", prompt, system_prompt)

    def generate_from_messages(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> str:
        return self._try_primary_first(
            "generate_from_messages", messages, system_prompt,
        )

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Any:
        if not self._using_fallback:
            try:
                async for chunk in self._primary.generate_stream(prompt, system_prompt):
                    yield chunk
                return
            except (LLMError, Exception) as e:
                logger.warning(
                    "Streaming no primário (%s) falhou: %s. A usar fallback (%s).",
                    self._primary.provider_name, e, self._fallback.provider_name,
                )
                self._using_fallback = True

        async for chunk in self._fallback.generate_stream(prompt, system_prompt):
            yield chunk

    def is_available(self) -> bool:
        if self._primary.is_available():
            self._using_fallback = False
            return True
        if self._fallback.is_available():
            self._using_fallback = True
            return True
        return False

    @property
    def provider_name(self) -> str:
        active = self._fallback if self._using_fallback else self._primary
        return f"FallbackChain({active.provider_name})"

    @property
    def available_models(self) -> List[Dict[str, Any]]:
        return self._primary.available_models + self._fallback.available_models

    @property
    def using_fallback(self) -> bool:
        """Indica se o sistema está atualmente a usar o fallback."""
        return self._using_fallback

    def reset(self) -> None:
        """Reseta a chain para tentar o primário novamente."""
        self._using_fallback = False
