"""
Uma instância só do app por pasta de dados.

Com o app na bandeja, abrir o atalho de novo criaria um segundo processo, com outro ícone e
notificações em dobro. A primeira instância cria um mutex com nome; a segunda percebe, acende
um evento com nome ("mostre a janela") e sai. Só Windows; em outros sistemas não faz nada.
"""

import ctypes
import hashlib
import sys
import threading
from pathlib import Path
from typing import Callable, Optional

ERROR_ALREADY_EXISTS = 183
EVENT_MODIFY_STATE = 0x0002
INFINITE = 0xFFFFFFFF


class SingleInstance:
    def __init__(self, data_dir: Path):
        # Pastas de dados diferentes (instalado x desenvolvimento) são apps independentes
        tag = hashlib.sha1(str(data_dir.resolve()).lower().encode()).hexdigest()[:12]
        self._mutex_name = f"Local\\StonksAI-{tag}"
        self._event_name = f"Local\\StonksAI-show-{tag}"
        self._mutex = None
        self._event = None
        self._k = ctypes.WinDLL("kernel32", use_last_error=True) if sys.platform == "win32" else None

    def acquire(self) -> bool:
        """True se esta é a primeira instância."""
        if not self._k:
            return True
        self._k.CreateMutexW.restype = ctypes.c_void_p
        self._mutex = self._k.CreateMutexW(None, False, self._mutex_name)
        if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
            return False
        self._k.CreateEventW.restype = ctypes.c_void_p
        self._event = self._k.CreateEventW(None, False, False, self._event_name)
        return True

    def signal_first(self) -> None:
        """Pede à instância que já está rodando para mostrar a janela."""
        if not self._k:
            return
        self._k.OpenEventW.restype = ctypes.c_void_p
        handle = self._k.OpenEventW(EVENT_MODIFY_STATE, False, self._event_name)
        if handle:
            self._k.SetEvent(ctypes.c_void_p(handle))
            self._k.CloseHandle(ctypes.c_void_p(handle))

    def on_signal(self, callback: Callable[[], None]) -> Optional[threading.Thread]:
        """Chama callback sempre que outra instância pedir para mostrar a janela."""
        if not self._k or not self._event:
            return None

        def wait() -> None:
            while self._k.WaitForSingleObject(ctypes.c_void_p(self._event), INFINITE) == 0:
                callback()

        t = threading.Thread(target=wait, daemon=True, name="single-instance")
        t.start()
        return t
