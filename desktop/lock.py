"""
Bloqueio do app por PIN.

Com um PIN definido, a API recusa as rotas de dados (423) até o PIN ser digitado, e volta
a bloquear depois de um tempo sem uso. O estado de desbloqueio vive só na memória: fechar
e abrir o app sempre pede o PIN de novo.

Protege contra quem senta no computador com o app aberto ou abre o app. Não criptografa o
banco: quem tem acesso aos arquivos do usuário no Windows ainda consegue ler os dados.

O PIN é guardado como hash scrypt com sal no config.yaml, nunca em texto. Erros seguidos
aumentam a espera entre tentativas.
"""

import hashlib
import hmac
import secrets
import threading
import time
from typing import Any, Dict, Optional

from stonks_ai.config import config

PIN_MIN, PIN_MAX = 4, 8
DEFAULT_TIMEOUT_MIN = 10
TIMEOUTS_MIN = (0, 5, 10, 30, 60)  # 0 = só bloqueia ao abrir o app
FREE_ATTEMPTS = 3
SCRYPT = {"n": 2**14, "r": 8, "p": 1}

_lock = threading.Lock()
_state = {"unlocked": False, "last_seen": 0.0, "failures": 0, "retry_at": 0.0}


class LockError(Exception):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


def _hash(pin: str, salt: bytes) -> str:
    digest = hashlib.scrypt(pin.encode(), salt=salt, **SCRYPT, dklen=32)
    return f"scrypt${salt.hex()}${digest.hex()}"


def _verify(pin: str, stored: str) -> bool:
    try:
        _, salt_hex, _ = stored.split("$")
        return hmac.compare_digest(_hash(pin, bytes.fromhex(salt_hex)), stored)
    except ValueError:
        return False


def _validate_pin(pin: str) -> None:
    if not (pin.isdigit() and PIN_MIN <= len(pin) <= PIN_MAX):
        raise LockError(f"O PIN deve ter de {PIN_MIN} a {PIN_MAX} números.")


def enabled() -> bool:
    return bool(config.get("security", "pin_hash", default=""))


def timeout_minutes() -> int:
    value = config.get("security", "lock_after_minutes", default=DEFAULT_TIMEOUT_MIN)
    return value if value in TIMEOUTS_MIN else DEFAULT_TIMEOUT_MIN


def is_locked(now: Optional[float] = None) -> bool:
    """Bloqueado = há PIN e (não foi desbloqueado ou passou o tempo sem uso)."""
    if not enabled():
        return False
    now = now or time.monotonic()
    with _lock:
        if not _state["unlocked"]:
            return True
        limit = timeout_minutes() * 60
        if limit and now - _state["last_seen"] > limit:
            _state["unlocked"] = False
            return True
        return False


def touch(now: Optional[float] = None) -> None:
    """Registra uso (cada chamada à API) para contar o tempo sem uso."""
    with _lock:
        _state["last_seen"] = now or time.monotonic()


def status() -> Dict[str, Any]:
    retry = max(0.0, _state["retry_at"] - time.monotonic())
    return {
        "enabled": enabled(),
        "locked": is_locked(),
        "timeout_minutes": timeout_minutes(),
        "retry_after_seconds": round(retry) if retry else 0,
    }


def unlock(pin: str, now: Optional[float] = None) -> None:
    now = now or time.monotonic()
    with _lock:
        if now < _state["retry_at"]:
            raise LockError(f"Muitas tentativas. Aguarde {round(_state['retry_at'] - now)} s.", 429)
        if _verify(pin, config.get("security", "pin_hash", default="")):
            _state.update(unlocked=True, last_seen=now, failures=0, retry_at=0.0)
            return
        _state["failures"] += 1
        extra = _state["failures"] - FREE_ATTEMPTS
        if extra > 0:
            # 5 s, 10 s, 20 s... até 5 minutos
            _state["retry_at"] = now + min(5 * 2 ** (extra - 1), 300)
    raise LockError("PIN incorreto.", 401)


def lock_now() -> None:
    with _lock:
        _state["unlocked"] = False


def set_pin(new_pin: str, current_pin: str = "") -> None:
    """Define, troca (pede o atual) ou remove o PIN (new_pin vazio, pede o atual)."""
    if enabled() and not _verify(current_pin, config.get("security", "pin_hash", default="")):
        raise LockError("PIN atual incorreto.", 401)
    if not new_pin:
        config.set("", "security", "pin_hash")
        return
    _validate_pin(new_pin)
    config.set(_hash(new_pin, secrets.token_bytes(16)), "security", "pin_hash")
    with _lock:
        _state.update(unlocked=True, last_seen=time.monotonic(), failures=0, retry_at=0.0)


def set_timeout(minutes: int) -> None:
    if minutes not in TIMEOUTS_MIN:
        raise LockError("Tempo de bloqueio inválido.")
    config.set(minutes, "security", "lock_after_minutes")


def _reset_for_tests() -> None:
    with _lock:
        _state.update(unlocked=False, last_seen=0.0, failures=0, retry_at=0.0)
