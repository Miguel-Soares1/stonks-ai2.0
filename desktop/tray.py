"""
Ícone na bandeja do Windows (perto do relógio) e notificações.

Com a janela fechada, o app continua rodando aqui para avisar dos alertas de preço-alvo.
Clique no ícone abre a janela; o menu tem "Sair", que encerra de verdade.
"""

import logging
from typing import Callable

import pystray
from PIL import Image, ImageDraw

logger = logging.getLogger("stonks_ai.desktop")


def _image(size: int = 64) -> Image.Image:
    """O mesmo desenho do ícone da janela: quadrado azul com a linha do gráfico subindo."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    s = size / 32
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=7 * s, fill=(31, 79, 216, 255))
    points = [(7 * s, 21 * s), (13 * s, 15 * s), (17 * s, 19 * s), (25 * s, 10 * s)]
    draw.line(points, fill="white", width=round(3 * s), joint="curve")
    return img


class Tray:
    def __init__(self, on_open: Callable[[], None], on_quit: Callable[[], None]):
        menu = pystray.Menu(
            pystray.MenuItem("Abrir Stonks AI", lambda: on_open(), default=True),
            pystray.MenuItem("Sair", lambda: on_quit()),
        )
        self._icon = pystray.Icon("StonksAI", _image(), "Stonks AI", menu=menu)

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
