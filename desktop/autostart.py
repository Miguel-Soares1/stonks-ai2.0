"""
Abrir com o Windows: uma entrada em HKCU\\...\\Run que inicia o app escondido na bandeja.

Só no app instalado (executável do PyInstaller): rodando pelo código-fonte, o comando
dependeria da pasta do projeto e do venv.
"""

import sys

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "StonksAI"


def supported() -> bool:
    return sys.platform == "win32" and bool(getattr(sys, "frozen", False))


def command() -> str:
    return f'"{sys.executable}" --tray'


def is_enabled() -> bool:
    if not supported():
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            return winreg.QueryValueEx(key, VALUE_NAME)[0] == command()
    except OSError:
        return False


def set_enabled(on: bool) -> None:
    if not supported():
        raise RuntimeError("Disponível só no app instalado.")
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if on:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command())
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass
