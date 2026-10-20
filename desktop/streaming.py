"""
Streaming de respostas da IA para o frontend.

Os providers expõem geradores assíncronos, mas alguns (Ollama) fazem I/O
bloqueante dentro deles. Para não travar o servidor, o gerador roda numa
thread própria com seu próprio event loop, e os pedaços chegam por uma fila.
"""

import asyncio
import queue
import threading
from typing import AsyncIterator, Callable, Iterator, Optional

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from stonks_ai.llm.base import BaseLLMProvider

_DONE = object()


def _iterate_in_thread(make_stream: Callable[[], AsyncIterator[str]]) -> Iterator[object]:
    q: "queue.Queue[object]" = queue.Queue()

    def worker() -> None:
        async def run() -> None:
            try:
                async for chunk in make_stream():
                    q.put(chunk)
            except Exception as e:  # repassado ao consumidor
                q.put(e)
            finally:
                q.put(_DONE)

        asyncio.run(run())

    threading.Thread(target=worker, daemon=True).start()
    while True:
        item = q.get()
        if item is _DONE:
            return
        yield item


def stream_text(
    make_stream: Callable[[], AsyncIterator[str]],
    on_complete: Optional[Callable[[str], None]] = None,
) -> StreamingResponse:
    """Resposta HTTP em texto puro que chega pedaço a pedaço."""

    def body() -> Iterator[str]:
        parts = []
        for item in _iterate_in_thread(make_stream):
            if isinstance(item, Exception):
                yield f"\n\n[Erro da IA: {item}]"
                return
            parts.append(item)
            yield item
        if on_complete:
            on_complete("".join(parts))

    return StreamingResponse(body(), media_type="text/plain; charset=utf-8")


def require_llm(llm: BaseLLMProvider) -> None:
    if not llm.is_available():
        raise HTTPException(
            status_code=503,
            detail="A IA não está disponível. Verifique se o Ollama está aberto, ou ajuste o provider em Ajustes.",
        )
