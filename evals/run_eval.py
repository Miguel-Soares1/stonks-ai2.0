"""
Avaliação dos modelos de IA do Stonks AI nas tarefas reais do app.

Cada caso de evals/casos.jsonl é enviado com o MESMO prompt que o app usa,
e a resposta é verificada automaticamente. O relatório sai em evals/resultados/.

Uso (a partir da raiz do projeto):
    python -m evals.run_eval                        # provider/modelo do config.yaml
    python -m evals.run_eval --model llama3.2:1b    # outro modelo do Ollama
    python -m evals.run_eval --only categorizacao   # só uma tarefa
"""

import argparse
import itertools
import json
import re
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from stonks_ai.collectors.finance.categorizer import build_categorization_prompt, parse_category
from stonks_ai.config import config
from stonks_ai.llm.factory import create_llm_client
from stonks_ai.llm.ollama_provider import OllamaProvider
from stonks_ai.llm.prompts import (
    FINANCIAL_ANALYSIS_SYSTEM_PROMPT,
    build_chat_system_prompt,
    format_goal_prompt,
    format_monthly_summary_prompt,
    format_stock_analysis_prompt,
)
from stonks_ai.models.category import DEFAULT_CATEGORIES

EVALS_DIR = Path(__file__).resolve().parent
CATEGORY_NAMES = [c["name"] for c in DEFAULT_CATEGORIES]

# Palavras muito comuns em cada idioma, para detectar respostas fora do português
_PT_WORDS = {"de", "que", "não", "para", "com", "uma", "os", "você", "seu", "sua", "mais", "é"}
_EN_WORDS = {"the", "and", "is", "of", "to", "you", "your", "with", "for", "this", "that"}


# ── Utilidades de texto e números ───────────────────────────────────────

def normalize(text: str) -> str:
    """Minúsculas e sem acentos, para comparar termos com tolerância."""
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def is_portuguese(text: str) -> bool:
    words = re.findall(r"[a-zà-ú]+", text.lower())
    pt = sum(w in _PT_WORDS for w in words)
    en = sum(w in _EN_WORDS for w in words)
    return pt >= en


def parse_amount(raw: str) -> Optional[float]:
    """Converte '1.234,56', '1,234.56', '58,00', '3.231' ou '12 mil' em float."""
    raw = raw.strip()
    mult = 1000.0 if raw.endswith("mil") else 1.0
    raw = raw.replace("mil", "").strip()
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".") if re.search(r",\d{1,2}$", raw) else raw.replace(",", "")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", raw):
        raw = raw.replace(".", "")
    try:
        return float(raw) * mult
    except ValueError:
        return None


_MONEY_RE = re.compile(r"(?:R\$|US\$|\$|BRL|USD)\s?(-?\d[\d.,]*(?:\s?mil)?)")


def money_values(text: str) -> List[float]:
    values = (parse_amount(m.group(1).rstrip(".,")) for m in _MONEY_RE.finditer(text))
    return [v for v in values if v is not None]


def numeric_leaves(data: Any) -> List[float]:
    if isinstance(data, bool):
        return []
    if isinstance(data, (int, float)):
        return [float(data)]
    if isinstance(data, dict):
        return [v for x in data.values() for v in numeric_leaves(x)]
    if isinstance(data, (list, tuple)):
        return [v for x in data for v in numeric_leaves(x)]
    return []


def grounded_values(data: Any) -> List[float]:
    """Valores presentes nos dados mais somas/diferenças simples entre pares."""
    base = [abs(v) for v in numeric_leaves(data)]
    derived = [a + b for a, b in itertools.combinations(base, 2)]
    derived += [abs(a - b) for a, b in itertools.combinations(base, 2)]
    return base + derived


_NUM_RE = re.compile(r"-?\d[\d.,]*")


def prompt_numbers(prompt: str) -> List[float]:
    values = (parse_amount(m.group(0).rstrip(".,")) for m in _NUM_RE.finditer(prompt))
    return [v for v in values if v is not None]


def unsupported_numbers(text: str, data: Any, prompt: str = "") -> List[float]:
    """Valores monetários citados na resposta que não batem com nada dos dados nem do prompt."""
    allowed = grounded_values([data, prompt_numbers(prompt)])
    out = []
    for v in money_values(text):
        tol = max(1.0, abs(v) * 0.005)
        if not any(abs(abs(v) - a) <= tol for a in allowed):
            out.append(v)
    return out


# ── Montagem dos prompts (idênticos aos do app) ─────────────────────────

def build_request(case: Dict[str, Any]) -> Dict[str, Optional[str]]:
    task = case["tarefa"]
    if task == "categorizacao":
        return {"prompt": build_categorization_prompt(case["entrada"], CATEGORY_NAMES), "system": None}
    if task in ("conceito", "seguranca"):
        return {"prompt": case["pergunta"], "system": build_chat_system_prompt(case["pergunta"])}
    if task == "resumo_mensal":
        d = dict(case["dados"])
        d["top_categories"] = [{"name": n, "amount": a, "percent": p} for n, a, p in d.pop("categorias")]
        return {"prompt": format_monthly_summary_prompt(d["month"], d["year"], d), "system": None}
    if task == "meta":
        return {"prompt": format_goal_prompt(**case["dados"]), "system": None}
    if task == "analise_acao":
        d = case["dados"]
        return {
            "prompt": format_stock_analysis_prompt(d["quote"], d.get("fundamentals")),
            "system": FINANCIAL_ANALYSIS_SYSTEM_PROMPT,
        }
    raise ValueError(f"Tarefa desconhecida: {task}")


# ── Verificação ─────────────────────────────────────────────────────────

def check(case: Dict[str, Any], response: str, prompt: str = "") -> Dict[str, Any]:
    result: Dict[str, Any] = {"ok": True, "motivos": []}

    if case["tarefa"] == "categorizacao":
        # Mesma regra do app (parse_category)
        chosen = parse_category(response, CATEGORY_NAMES)
        result["escolhida"] = chosen
        if chosen != case["esperado"]:
            result["ok"] = False
            result["motivos"].append(f"esperado {case['esperado']}, veio {chosen or 'nenhuma'}")
        return result

    norm = normalize(response)
    for group in case.get("deve_conter", []):
        if not any(normalize(term) in norm for term in group):
            result["ok"] = False
            result["motivos"].append(f"faltou um de: {', '.join(group)}")

    if not is_portuguese(response):
        result["ok"] = False
        result["motivos"].append("resposta fora do português")

    if "dados" in case:
        result["numeros_sem_lastro"] = unsupported_numbers(response, case["dados"], prompt)
        result["numeros_citados"] = len(money_values(response))
    return result


# ── Execução ────────────────────────────────────────────────────────────

def make_provider(model: Optional[str], temperature: float):
    if model:
        provider = OllamaProvider(
            model=model,
            endpoint=config.get("llm", "endpoint", default="http://localhost:11434"),
            temperature=temperature,
            max_tokens=config.get("llm", "max_tokens", default=2048),
            timeout=config.get("llm", "timeout_seconds", default=120),
            num_ctx=config.get("llm", "num_ctx", default=4096),
            keep_alive=config.get("llm", "keep_alive", default="2m"),
        )
    else:
        provider = create_llm_client(config)
        provider.temperature = temperature
    return provider


def ollama_memory_gb(model: str) -> Optional[float]:
    """RAM/VRAM ocupada pelo modelo carregado, segundo o Ollama (/api/ps)."""
    endpoint = config.get("llm", "endpoint", default="http://localhost:11434").rstrip("/")
    try:
        for m in httpx.get(f"{endpoint}/api/ps", timeout=5).json().get("models", []):
            if m.get("name") == model or m.get("model") == model:
                return round(m.get("size", 0) / 1024**3, 2)
    except Exception:
        pass
    return None


def run(cases: List[Dict[str, Any]], provider, model_name: str) -> Dict[str, Any]:
    results = []
    memory = None
    for i, case in enumerate(cases, 1):
        req = build_request(case)
        start = time.perf_counter()
        try:
            response = provider.generate(req["prompt"], system_prompt=req["system"])
            error = None
        except Exception as e:  # registra e segue para o próximo caso
            response, error = "", str(e)
        elapsed = time.perf_counter() - start

        verdict = check(case, response, req["prompt"]) if not error else {"ok": False, "motivos": [f"erro: {error}"]}
        results.append({"id": case["id"], "tarefa": case["tarefa"], "conjunto": case.get("conjunto", "original"),
                        "segundos": round(elapsed, 2),
                        "resposta": response, **verdict})
        if memory is None:
            memory = ollama_memory_gb(model_name)
        mark = "ok " if verdict["ok"] else "ERR"
        print(f"[{i:>3}/{len(cases)}] {mark} {case['id']:<8} {elapsed:6.1f}s  {'; '.join(verdict['motivos'])}")

    return {"modelo": model_name, "data": datetime.now().isoformat(timespec="seconds"),
            "memoria_gb": memory, "resultados": results}


def summarize(report: Dict[str, Any]) -> Dict[str, Any]:
    rows = report["resultados"]
    by_task: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        t = by_task.setdefault(r["tarefa"], {"total": 0, "acertos": 0, "segundos": 0.0,
                                             "citados": 0, "sem_lastro": 0})
        t["total"] += 1
        t["acertos"] += int(r["ok"])
        t["segundos"] += r["segundos"]
        t["citados"] += r.get("numeros_citados", 0)
        t["sem_lastro"] += len(r.get("numeros_sem_lastro", []))
    by_set: Dict[str, Dict[str, int]] = {}
    for r in rows:
        c = by_set.setdefault(r.get("conjunto", "original"), {"total": 0, "acertos": 0})
        c["total"] += 1
        c["acertos"] += int(r["ok"])
    total = len(rows)
    return {
        "por_conjunto": by_set,
        "acerto_geral": sum(r["ok"] for r in rows) / total if total else 0,
        "tempo_medio": sum(r["segundos"] for r in rows) / total if total else 0,
        "por_tarefa": by_task,
    }


def write_markdown(report: Dict[str, Any], summary: Dict[str, Any], path: Path) -> None:
    lines = [
        f"# Avaliação: {report['modelo']}",
        "",
        f"- Data: {report['data']}",
        f"- Acerto geral: **{summary['acerto_geral']:.0%}**",
        f"- Tempo médio por resposta: {summary['tempo_medio']:.1f} s",
        f"- Memória do modelo carregado (Ollama): "
        f"{report['memoria_gb'] if report['memoria_gb'] is not None else 'n/d'} GB",
        *[f"- Acerto no conjunto {k}: {v['acertos']}/{v['total']} ({v['acertos'] / v['total']:.0%})"
          for k, v in summary["por_conjunto"].items()],
        "",
        "| Tarefa | Acertos | Tempo médio | Números sem lastro |",
        "|---|---|---|---|",
    ]
    for task, t in summary["por_tarefa"].items():
        lastro = f"{t['sem_lastro']} de {t['citados']}" if t["citados"] else "—"
        lines.append(f"| {task} | {t['acertos']}/{t['total']} | {t['segundos'] / t['total']:.1f} s | {lastro} |")

    failures = [r for r in report["resultados"] if not r["ok"]]
    if failures:
        lines += ["", "## Falhas", ""]
        for r in failures:
            excerpt = " ".join(r["resposta"].split())[:240]
            lines.append(f"- **{r['id']}**: {'; '.join(r['motivos'])}  \n  > {excerpt or '(sem resposta)'}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Avalia um modelo de IA nas tarefas do Stonks AI.")
    parser.add_argument("--model", help="Modelo do Ollama (padrão: provider/modelo do config.yaml)")
    parser.add_argument("--only", help="Roda só uma tarefa (ex.: categorizacao, conceito, meta)")
    parser.add_argument("--temperature", type=float, default=0.0,
                        help="Temperatura (padrão 0 para resultados comparáveis entre modelos)")
    parser.add_argument("--casos", type=Path, default=EVALS_DIR / "casos.jsonl")
    parser.add_argument("--conjunto", help="Roda só um conjunto de casos (original ou novo)")
    parser.add_argument("--rotulo", default="", help="Texto extra no nome do relatório (ex.: antes, depois)")
    args = parser.parse_args()

    cases = [json.loads(line) for line in args.casos.read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.only:
        cases = [c for c in cases if c["tarefa"] == args.only]
    if args.conjunto:
        cases = [c for c in cases if c.get("conjunto", "original") == args.conjunto]

    model_name = args.model or config.get("llm", "model", default="")
    provider = make_provider(args.model, args.temperature)
    print(f"Avaliando {model_name} em {len(cases)} casos...\n")

    report = run(cases, provider, model_name)
    summary = summarize(report)
    report["resumo"] = summary

    out_dir = EVALS_DIR / "resultados"
    out_dir.mkdir(exist_ok=True)
    label = f"_{args.rotulo}" if args.rotulo else ""
    stem = f"{datetime.now():%Y%m%d-%H%M}_{re.sub(r'[^A-Za-z0-9.-]+', '-', model_name)}{label}"
    (out_dir / f"{stem}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(report, summary, out_dir / f"{stem}.md")

    print(f"\nAcerto geral: {summary['acerto_geral']:.0%}   Tempo médio: {summary['tempo_medio']:.1f} s"
          f"   Memória: {report['memoria_gb']} GB")
    print(f"Relatório: {out_dir / (stem + '.md')}")


if __name__ == "__main__":
    main()
