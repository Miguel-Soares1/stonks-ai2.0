"""
Ponto de entrada do Stonks AI Desktop.

Sobe a API local numa porta livre e abre uma janela nativa (WebView2 no Windows).

Uso (dev):
    python -m desktop.app
"""

import os
import secrets
import socket
import sys
import threading
import time

import uvicorn
import webview

from stonks_ai.config import DATA_DIR


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


def main() -> None:
    _redirect_output_if_windowed()

    # Token novo a cada abertura: só esta janela consegue chamar a API local.
    # STONKS_API_TOKEN pode ser definido de fora apenas para testes automatizados.
    token = os.environ.get("STONKS_API_TOKEN") or secrets.token_urlsafe(32)
    os.environ["STONKS_API_TOKEN"] = token

    port = _free_port()
    server = _start_server(port)

    webview.create_window(
        "Stonks AI",
        f"http://127.0.0.1:{port}/?t={token}",
        width=1280,
        height=840,
        min_size=(960, 640),
        background_color="#000000" if _system_prefers_dark() else "#F2F4F7",
    )
    try:
        # private_mode: a WebView não guarda cache, cookies nem histórico em disco
        webview.start(private_mode=True)
    finally:
        server.should_exit = True


if __name__ == "__main__":
    main()
