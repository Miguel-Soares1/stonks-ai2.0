"""
Base de conhecimento financeiro local (RAG leve, sem modelo de embeddings).

Os verbetes ficam em base_conhecimento.md. Para cada pergunta, os verbetes mais
relevantes são encontrados por BM25 sobre palavras normalizadas (sem acento) e
entram no prompt do assistente. Assim um modelo pequeno responde com fatos
conferidos em vez de "lembrar" (e inventar) da própria memória.
"""

import math
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List

KB_FILE = "base_conhecimento.md"

# Palavras sem valor de busca
_STOPWORDS = set("""
a o e é de da do das dos em no na nos nas um uma uns umas para por com sem que qual quais
como quando onde ou se ao aos à às seu sua seus suas meu minha eu você voce isso isto esse essa
mais menos muito pouco já ja não nao sim ser ter tem há ha foi são sao está esta estão estao
me te lhe nos vos eles elas ele ela vai vou pode posso devo deve sobre entre até ate também tambem
explique explica diga fale quero saber o que
bom boa dia tarde noite ola oi obrigado obrigada valeu
""".split())


@dataclass
class Entry:
    title: str
    terms: str
    body: str

    def as_text(self) -> str:
        return f"### {self.title}\n{self.body}"


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def _tokens(text: str) -> List[str]:
    words = re.findall(r"[a-z0-9+/]+", _normalize(text))
    out = []
    for w in words:
        w = w.strip("/")
        if len(w) < 2 or w in _STOPWORDS:
            continue
        # Plural simples: "fundos" e "fundo" contam como a mesma palavra
        if len(w) > 4 and w.endswith("s"):
            w = w[:-1]
        out.append(w)
    return out


def _kb_path() -> Path:
    # No executável (PyInstaller) os arquivos de dados ficam em sys._MEIPASS
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent.parent))
    packaged = base / "stonks_ai" / "knowledge" / KB_FILE
    return packaged if packaged.exists() else Path(__file__).resolve().parent / KB_FILE


def _parse(markdown: str) -> List[Entry]:
    entries = []
    for block in re.split(r"^## ", markdown, flags=re.M)[1:]:
        lines = block.strip().splitlines()
        title = lines[0].strip()
        terms = ""
        body_lines = []
        for line in lines[1:]:
            if line.startswith("Termos:"):
                terms = line[len("Termos:"):].strip()
            elif line.strip():
                body_lines.append(line.strip())
        entries.append(Entry(title=title, terms=terms, body=" ".join(body_lines)))
    return entries


class KnowledgeBase:
    """Índice BM25 sobre os verbetes. Título e termos pesam mais que o corpo."""

    K1 = 1.4
    B = 0.75
    # Palavra da pergunta que é o próprio assunto do verbete ("CDB" no verbete CDB)
    TITLE_BONUS = 3.0

    def __init__(self, entries: List[Entry]):
        self.entries = entries
        self.docs = [
            Counter(_tokens(f"{e.title} {e.title} {e.terms} {e.terms} {e.terms} {e.body}"))
            for e in entries
        ]
        self.titles = [set(_tokens(e.title)) for e in entries]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg_len = sum(self.lengths) / max(len(self.lengths), 1)
        df = Counter(t for d in self.docs for t in d)
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query: str, k: int = 3, min_score: float = 2.0) -> List[Entry]:
        q = set(_tokens(query))
        scored = []
        for entry, doc, length, title in zip(self.entries, self.docs, self.lengths, self.titles):
            score = self.TITLE_BONUS * len(q & title)
            for t in q:
                tf = doc.get(t, 0)
                if not tf:
                    continue
                norm = tf * (self.K1 + 1) / (tf + self.K1 * (1 - self.B + self.B * length / self.avg_len))
                score += self.idf[t] * norm
            if score >= min_score:
                scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:k]]


@lru_cache(maxsize=1)
def knowledge_base() -> KnowledgeBase:
    return KnowledgeBase(_parse(_kb_path().read_text(encoding="utf-8")))


def context_for(question: str, k: int = 4) -> str:
    """Verbetes relevantes para a pergunta, prontos para entrar no prompt ("" se nada servir)."""
    return "\n\n".join(e.as_text() for e in knowledge_base().search(question, k=k))
