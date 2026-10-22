"""
Avaliação das ferramentas do chat: a IA escolhe a ferramenta certa, com os argumentos certos?

Mede só a primeira decisão (qual ferramenta chamar e com quais argumentos), pelo mesmo caminho
do chat do app: mesmo prompt, mesmas ferramentas, histórico como contexto e consulta garantida
dos ativos citados. Nenhuma ferramenta é executada: não precisa
de internet nem de dados, e cada caso leva poucos segundos.

Uso (a partir da raiz do projeto):
    python -m evals.tools_eval                              # modelo do config.yaml
    python -m evals.tools_eval --model qwen2.5:3b qwen2.5:1.5b
"""

import argparse
import asyncio
import json
import time
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import httpx

from stonks_ai.config import config
from stonks_ai.llm.factory import create_llm_client
from stonks_ai.llm.prompts import build_chat_system_prompt, chat_query_from_messages
from stonks_ai.llm.tools import TOOLS, _date_arg, build_convo, normalize_call, prefetch_calls, tools_prompt

ROOT = Path(__file__).parent
CASES = ROOT / "casos_ferramentas.jsonl"
RESULTS = ROOT / "resultados"


def _plain(text: Any) -> str:
    s = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return s.lower().strip()


def _matches(call: Dict[str, Any], want: Dict[str, Any]) -> bool:
    if call["name"] != want["nome"]:
        return False
    args = call["arguments"]
    for key, value in want.items():
        if key == "nome":
            continue
        got = args.get(key)
        if key == "ticker":
            if _plain(got).upper().replace("-USD", "") != value:
                return False
        elif key in ("valor", "preco_alvo"):  # número: 23.9, "23,90" e "R$ 23,90" valem
            try:
                if abs(float(str(got).replace("R$", "").replace(",", ".")) - value) > 0.005:
                    return False
            except (TypeError, ValueError):
                return False
        elif key == "data":  # dias atrás: 1 = ontem ("ontem" ou a data, tanto faz)
            try:
                if _date_arg(got, date.today()) != date.today() - timedelta(days=value):
                    return False
            except ValueError:
                return False
        elif key == "mes":
            try:
                if int(got) != value:
                    return False
            except (TypeError, ValueError):
                return False
        elif _plain(value) not in _plain(got):  # busca e tipo: contém
            return False
    return True


def judge(calls: List[Dict[str, Any]], case: Dict[str, Any]) -> bool:
    """Passa se as chamadas batem com o esperado (ou com uma alternativa aceita), na ordem que for."""
    for option in [case["esperado"], *case.get("aceita", [])]:
        if len(calls) != len(option):
            continue
        left = list(calls)
        if all(any(_matches(c, w) and not left.remove(c) for c in left) for w in option):
            return True
    return False


async def first_decision(llm, question: str, history: List[Dict[str, str]] = ()) -> List[Dict[str, Any]]:
    """O que o app consulta para a pergunta, pelo mesmo caminho do chat (desktop/routes/assistant.py).

    history: conversa anterior, como o app manda (só papel e texto), para as perguntas de seguimento.
    Ativo citado na pergunta é consultado pelo próprio app (prefetch_calls); sem ele, vale a
    primeira decisão do modelo.
    """
    messages = [*history, {"role": "user", "content": question}]
    forced = prefetch_calls(messages)
    if forced:
        return forced
    system = build_chat_system_prompt(chat_query_from_messages(messages)) + tools_prompt()
    calls: List[Dict[str, Any]] = []
    async for event in llm.stream_chat(build_convo(messages, system), tools=TOOLS):
        calls.extend(normalize_call(c, question) for c in event.get("tool_calls") or [])
    return calls


def memory_gb(model: str) -> float:
    try:
        endpoint = config.get("llm", "endpoint", default="http://localhost:11434").rstrip("/")
        for m in httpx.get(f"{endpoint}/api/ps", timeout=5).json().get("models", []):
            if m.get("name") == model:
                return round(m.get("size", 0) / 1024**3, 2)
    except Exception:
        pass
    return 0.0


def run(model: str, cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    llm = create_llm_client(temperature=0.0)
    llm.model = model
    rows = []
    asyncio.run(first_decision(llm, "Oi"))  # carrega o modelo antes de medir
    for case in cases:
        t0 = time.time()
        try:
            calls = asyncio.run(first_decision(llm, case["pergunta"], case.get("historico", [])))
            error = None
        except Exception as e:
            calls, error = [], str(e)
        rows.append({**case, "chamadas": calls, "ok": not error and judge(calls, case), "erro": error,
                     "segundos": round(time.time() - t0, 2)})
        print(f"  {'ok ' if rows[-1]['ok'] else 'ERR'} {case['id']}: "
              f"{', '.join(c['name'] + json.dumps(c['arguments'], ensure_ascii=False) for c in calls) or '(nenhuma)'}")
    hits = sum(r["ok"] for r in rows)
    return {"modelo": model, "acertos": hits, "total": len(rows), "percentual": round(hits / len(rows) * 100),
            "tempo_medio": round(sum(r["segundos"] for r in rows) / len(rows), 2),
            "memoria_gb": memory_gb(model), "casos": rows}


def report(results: List[Dict[str, Any]]) -> str:
    lines = [f"# Ferramentas do chat — {datetime.now():%d/%m/%Y %H:%M}", "",
             "| Modelo | Acertos | Tempo médio da decisão | Memória |", "|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['modelo']} | {r['acertos']}/{r['total']} ({r['percentual']}%) | {r['tempo_medio']} s "
                     f"| {r['memoria_gb']} GB |")
    for r in results:
        wrong = [c for c in r["casos"] if not c["ok"]]
        lines += ["", f"## Erros de {r['modelo']}", ""]
        lines += [f"- `{c['id']}` {c['pergunta']} → "
                  + (", ".join(f"{x['name']}({json.dumps(x['arguments'], ensure_ascii=False)})" for x in c["chamadas"])
                     or c["erro"] or "nenhuma ferramenta") for c in wrong] or ["Nenhum."]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--model", nargs="+", help="Modelos do Ollama (padrão: o do config.yaml)")
    args = parser.parse_args()
    cases = [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines() if line.strip()]
    models = args.model or [config.get("llm", "model", default="qwen2.5:3b")]
    results = []
    for model in models:
        print(f"{model}:")
        results.append(run(model, cases))
    RESULTS.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    name = "_".join(m.replace(":", "-") for m in models)
    (RESULTS / f"{stamp}_ferramentas_{name}.md").write_text(report(results), encoding="utf-8")
    (RESULTS / f"{stamp}_ferramentas_{name}.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(report(results).split("\n## ")[0])


if __name__ == "__main__":
    main()
