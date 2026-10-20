"""
Guarda a chave da API da IA no cofre do sistema (Gerenciador de Credenciais no Windows).

No config.yaml fica só o marcador KEYRING_MARKER; a chave em si nunca vai para o disco
em texto puro. Referências a variáveis de ambiente (${NOME}) continuam no config, porque
não são segredo. Sem cofre disponível (ex.: Linux sem serviço de chaves, Streamlit Cloud),
a chave volta a ser salva no config, como antes.
"""

import logging
from typing import Any

logger = logging.getLogger("stonks_ai.credentials")

KEYRING_SERVICE = "StonksAI"
KEYRING_USER = "llm_api_key"
KEYRING_MARKER = "@keyring"


def _keyring():
    try:
        import keyring
        from keyring.backends.fail import Keyring as FailKeyring

        if isinstance(keyring.get_keyring(), FailKeyring):
            return None
        return keyring
    except Exception:
        return None


def store_api_key(value: str) -> str:
    """Salva a chave no cofre e devolve o que deve ir para o config.yaml."""
    value = (value or "").strip()
    if value == KEYRING_MARKER:
        return value
    kr = _keyring()
    if not value or value.startswith("${"):
        if kr:
            try:
                kr.delete_password(KEYRING_SERVICE, KEYRING_USER)
            except Exception:
                pass  # não havia chave salva
        return value
    if kr:
        try:
            kr.set_password(KEYRING_SERVICE, KEYRING_USER, value)
            return KEYRING_MARKER
        except Exception as e:
            logger.warning("Cofre do sistema indisponível; a chave ficará no config.yaml: %s", e)
    return value


def resolve_api_key(raw: str) -> str:
    """Converte o valor do config na chave de verdade (lendo o cofre, se for o marcador)."""
    if raw != KEYRING_MARKER:
        return raw or ""
    kr = _keyring()
    if not kr:
        return ""
    try:
        return kr.get_password(KEYRING_SERVICE, KEYRING_USER) or ""
    except Exception:
        return ""


def migrate_plaintext_key(cfg: Any) -> bool:
    """Move para o cofre uma chave que ainda esteja em texto puro no config. True se moveu."""
    raw = cfg.get("llm", "api_key", default="") or ""
    if not raw or raw == KEYRING_MARKER or raw.startswith("${"):
        return False
    stored = store_api_key(raw)
    if stored == KEYRING_MARKER:
        cfg.set(stored, "llm", "api_key")
        return True
    return False
