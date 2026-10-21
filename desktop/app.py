"""
Ponto de entrada do Stonks AI Desktop.

Sobe a API local numa porta livre e abre uma janela nativa (WebView2 no Windows).
Fechar a janela deixa o app na bandeja, verificando os alertas de preço-alvo; "Sair" no
menu do ícone encerra de verdade (ajuste em Ajustes → Segundo plano).

Uso (dev):
    python -m desktop.app           # abre a janela
    python -m desktop.app --tray    # começa escondido na bandeja (usado ao abrir com o Windows)
"""

import os
import secrets
import socket
import sys
import threading
import time
from datetime import datetime

import logging

import uvicorn
import webview

from desktop.icon import ICON_PATH
from desktop.single_instance import SingleInstance
from stonks_ai import price_alerts
from stonks_ai.config import DATA_DIR, config

logger = logging.getLogger("stonks_ai.desktop")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_server(port: int) -> uvicorn.Server:
    from desktop.api import app

    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", log_config=None)
    )
    threading.Thread(target=server.run, daemon=True).start()
    deadline = time.monotonic() + 15
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("A API local não iniciou em 15 segundos.")
        time.sleep(0.05)
    return server


def _redirect_output_if_windowed() -> None:
    """No .exe sem console, stdout/stderr são None; manda tudo para um log em DATA_DIR."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    log = open(DATA_DIR / "desktop.log", "a", encoding="utf-8", buffering=1)
    sys.stdout = sys.stdout or log
    sys.stderr = sys.stderr or log


def _system_prefers_dark() -> bool:
    """Lê o tema do Windows, para a janela não piscar em branco ao abrir no modo escuro."""
    try:
        import winreg

        key = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
            return winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
    except (ImportError, OSError):
        return False


def _watch_prices(notify, stop: threading.Event) -> None:
    """Verifica os preços-alvo ao abrir e a cada 5 minutos no horário de pregão."""
    from desktop.state import financial_agent

    def fetch(ticker: str, exchange: str):
        return financial_agent().get_quote(ticker, exchange)

    first = True
    while not stop.is_set():
        if first or price_alerts.in_market_hours(datetime.now()):
            try:
                for alert in price_alerts.check(fetch):
                    notify(alert["title"], alert["message"])
            except Exception as e:  # sem internet, banco ocupado: tenta na próxima rodada
                logger.warning("Verificação de preço-alvo falhou: %s", e)
            first = False
        stop.wait(price_alerts.CHECK_INTERVAL_SECONDS)


def _set_app_id() -> None:
    """Barra de tarefas com a logo do app, não a do python.exe (que ela usaria rodando pelo código-fonte)."""
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("StonksAI.Desktop")
        except Exception:
            pass


def main() -> None:
    _redirect_output_if_windowed()
    _set_app_id()
    start_hidden = "--tray" in sys.argv[1:]

    # Já está rodando (talvez escondido na bandeja): pede para mostrar a janela e sai
    instance = SingleInstance(DATA_DIR)
    if not instance.acquire():
        instance.signal_first()
        return

    # Token novo a cada abertura: só esta janela consegue chamar a API local.
    # STONKS_API_TOKEN pode ser definido de fora apenas para testes automatizados.
    token = os.environ.get("STONKS_API_TOKEN") or secrets.token_urlsafe(32)
    os.environ["STONKS_API_TOKEN"] = token

    port = _free_port()
    server = _start_server(port)

    window = webview.create_window(
        "Stonks AI",
        f"http://127.0.0.1:{port}/?t={token}",
        width=1280,
        height=840,
        min_size=(960, 640),
        hidden=start_hidden,
        background_color="#000000" if _system_prefers_dark() else "#F2F4F7",
    )
    quitting = threading.Event()

    def show_window() -> None:
        window.show()
        window.restore()

    def quit_app() -> None:
        quitting.set()
        window.destroy()

    from desktop.tray import Tray  # pystray só é carregado no app de verdade, não na API

    tray = Tray(on_open=show_window, on_quit=quit_app)
    tray.start()
    instance.on_signal(show_window)

    def on_closing() -> bool:
        if quitting.is_set() or not config.get("desktop", "close_to_tray", default=True):
            quitting.set()
            return True
        # Cancela o fechamento e esconde depois que o evento terminar (chamar hide() aqui
        # dentro, na thread da janela, pode travar)
        threading.Thread(target=window.hide, daemon=True).start()
        if not config.get("desktop", "tray_hint_shown", default=False):
            config.set(True, "desktop", "tray_hint_shown")
            tray.notify("O Stonks AI continua na bandeja",
                        "Ele avisa quando um ativo da watchlist chegar ao preço-alvo. "
                        "Para fechar de vez, clique no ícone com o botão direito e escolha Sair.")
        return False

    window.events.closing += on_closing

    stop_watch = threading.Event()
    threading.Thread(target=_watch_prices, args=(tray.notify, stop_watch), daemon=True, name="price-alerts").start()
    try:
        # private_mode: a WebView não guarda cache, cookies nem histórico em disco
        # icon: sem ele, a janela pega o ícone do executável (o do Python, rodando pelo código-fonte)
        webview.start(private_mode=True, icon=str(ICON_PATH) if ICON_PATH.exists() else None)
    finally:
        stop_watch.set()
        tray.stop()
        server.should_exit = True


if __name__ == "__main__":
    main()
