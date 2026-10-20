"""Rota do assistente: conversa com a IA em streaming."""

from typing import List, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from desktop.state import financial_agent
from desktop.streaming import require_llm, stream_text
from stonks_ai.llm.prompts import build_chat_system_prompt, chat_query_from_messages

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
    # Verbetes da base de conhecimento relevantes para a pergunta entram no prompt
    system_prompt = build_chat_system_prompt(chat_query_from_messages(messages))
    return stream_text(lambda: llm.generate_stream_from_messages(messages, system_prompt=system_prompt))
