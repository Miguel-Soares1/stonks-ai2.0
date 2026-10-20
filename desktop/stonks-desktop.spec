# -*- mode: python ; coding: utf-8 -*-
# Build do Stonks AI Desktop (pasta única, sem console).
#
# Uso, a partir da raiz do projeto:
#     pyinstaller desktop/stonks-desktop.spec --noconfirm
#
# Saída: dist/StonksAI/StonksAI.exe

from pathlib import Path

ROOT = Path(SPECPATH).parent

a = Analysis(
    [str(ROOT / "desktop" / "app.py")],
    pathex=[str(ROOT)],
    datas=[
        (str(ROOT / "desktop" / "frontend"), "desktop/frontend"),
        (str(ROOT / "stonks_ai" / "knowledge" / "base_conhecimento.md"), "stonks_ai/knowledge"),
    ],
    hiddenimports=[
        "desktop.api",
        # uvicorn carrega estes módulos dinamicamente
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
    ],
    excludes=[
        # Só a interface Streamlit/CLI usa estes; o app desktop não precisa
        "streamlit", "plotly", "plotext", "matplotlib", "IPython", "jupyter",
        "pytest", "tkinter",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="StonksAI",
    console=False,
    upx=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    upx=False,
    name="StonksAI",
)
