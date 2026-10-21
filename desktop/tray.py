"""
Ícone na bandeja do Windows (perto do relógio) e notificações.

Com a janela fechada, o app continua rodando aqui para avisar dos alertas de preço-alvo.
Clique no ícone abre a janela; o menu tem "Sair", que encerra de verdade.
"""

import logging
from typing import Callable

import pystray

from desktop.icon import image

logger = logging.getLogger("stonks_ai.desktop")


class Tray:
    def __init__(self, on_open: Callable[[], None], on_quit: Callable[[], None]):
        menu = pystray.Menu(
            pystray.MenuItem("Abrir Stonks AI", lambda: on_open(), default=True),
            pystray.MenuItem("Sair", lambda: on_quit()),
        )
        self._icon = pystray.Icon("StonksAI", image(64), "Stonks AI", menu=menu)

    def start(self) -> None:
        # No Windows, o ícone roda na própria thread; a janela fica com a thread principal
        self._icon.run_detached()

    def notify(self, title: str, message: str) -> None:
        try:
            self._icon.notify(message, title)
        except Exception as e:  # notificação nunca derruba o app
            logger.warning("Notificação falhou: %s", e)

    def stop(self) -> None:
        try:
            self._icon.stop()
        except Exception:
            pass
