"""
API local do Stonks AI Desktop.

Expõe os agentes existentes como endpoints JSON e serve o frontend estático.
Roda apenas em 127.0.0.1, dentro do processo do app desktop.
"""

import logging
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from desktop import lock
from desktop.routes import assistant, finance, market, portfolio, reports, settings
from desktop.state import personal_agent
from stonks_ai import backup
from stonks_ai.agents.base_agent import AgentError
from stonks_ai.database import db
from stonks_ai.utils import recurrence

FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"

# Token gerado pelo app desktop a cada abertura (desktop/app.py). Sem ele, as rotas /api
# ficam abertas: isso só acontece rodando a API à mão em modo desenvolvimento.
API_TOKEN = os.environ.get("STONKS_API_TOKEN", "")
TOKEN_HEADER = "x-stonks-token"
LOCK_FREE_PATHS = {"/api/status", "/api/boot"}

SECURITY_HEADERS = {
    # Só scripts e estilos do próprio app; nenhum recurso externo; não pode ser embutido em outro site
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; "
        "frame-ancestors 'none'; form-action 'self'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}

logger = logging.getLogger("stonks_ai.desktop")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not API_TOKEN:
        logger.warning("API local sem token (modo desenvolvimento). Não exponha esta porta.")
    # Equivalente ao `stonks init`: tabelas, categorias, contas e alertas padrão.
    # Só cria o que falta, então é seguro rodar a cada abertura do app.
    db.initialize()
    try:
        personal_agent().initialize()
    except AgentError as e:
        logger.warning("Inicialização das finanças pessoais falhou: %s", e)
    try:
        recurrence.generate_due()
    except Exception as e:
        logger.warning("Geração das transações recorrentes falhou: %s", e)
    try:
        if backup.auto_backup_if_due():
            logger.info("Backup semanal criado.")
    except Exception as e:  # backup nunca impede o app de abrir
        logger.warning("Backup automático falhou: %s", e)
    yield


app = FastAPI(title="Stonks AI", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

# Só responde a quem chama pelo endereço local (bloqueia ataques de DNS rebinding)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])


@app.middleware("http")
async def protect(request: Request, call_next):
    path = request.url.path
    if API_TOKEN and path.startswith("/api/"):
        sent = request.headers.get(TOKEN_HEADER, "")
        if not secrets.compare_digest(sent.encode(), API_TOKEN.encode()):
            return JSONResponse(status_code=401, content={"detail": "Acesso negado."}, headers=SECURITY_HEADERS)
    # Com PIN, os dados só saem depois de desbloquear; status e as rotas do bloqueio ficam livres
    if path.startswith("/api/") and path not in LOCK_FREE_PATHS and not path.startswith("/api/lock"):
        if lock.is_locked():
            return JSONResponse(status_code=423, content={"detail": "App bloqueado. Digite o PIN."}, headers=SECURITY_HEADERS)
        lock.touch()
    response = await call_next(request)
    response.headers.update(SECURITY_HEADERS)
    return response


for module in (finance, market, portfolio, reports, assistant, settings):
    app.include_router(module.router)


@app.exception_handler(AgentError)
def agent_error(_: Request, exc: AgentError) -> JSONResponse:
    """Erros de regra de negócio dos agentes viram 400 com a mensagem original."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


# Montado por último para não capturar as rotas /api
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
