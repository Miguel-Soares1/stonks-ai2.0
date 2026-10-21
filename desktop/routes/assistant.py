"""Rota do assistente: conversa com a IA em streaming."""

from typing import List, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from desktop.state import financial_agent, personal_agent
from desktop.streaming import require_llm, stream_text
from stonks_ai.llm.prompts import build_chat_system_prompt, chat_query_from_messages
from stonks_ai.llm.tools import Toolbox, chat_with_tools, tools_prompt

router = APIRouter(prefix="/api")

# Mensagens anteriores enviadas como contexto (as mais recentes)
HISTORY_LIMIT = 10


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatIn(BaseModel):
    messages: List[Message] = Field(min_length=1)


@router.post("/chat")
def chat(body: ChatIn):
    llm = financial_agent().llm
    require_llm(llm)
    messages = [m.model_dump() for m in body.messages[-HISTORY_LIMIT:]]
    # Verbetes da base de conhecimento relevantes para a pergunta entram no prompt, mais as
    # instruções das ferramentas (cotações e dados do usuário, ADR 026)
    system_prompt = build_chat_system_prompt(chat_query_from_messages(messages)) + tools_prompt()
    toolbox = Toolbox(financial_agent(), personal_agent())
    return stream_text(lambda: chat_with_tools(llm, messages, system_prompt, toolbox))
