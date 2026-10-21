"""
Ferramentas da IA: o chat consulta dados reais do app em vez de responder de memória (ADR 026).

O modelo recebe a lista de ferramentas (TOOLS), decide se precisa de alguma, o app executa
(Toolbox) e devolve o resultado; o modelo então responde com os números de verdade.
Só leitura: nenhuma ferramenta muda dados.

Os resultados são curtos e já formatados ("R$ 1.234,56", "+1,5%"): modelos pequenos erram
menos repetindo um número pronto do que formatando um float.
"""

import ast
import calendar
import json
import operator
import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

from sqlalchemy import func, or_

from stonks_ai.llm.base import LLMError

logger = logging.getLogger("stonks_ai.llm.tools")

# Marca uma linha de status no texto do chat ("Consultando cotação de PETR4"); a tela tira
# essas linhas da resposta e mostra à parte (desktop/frontend/js/chat.js)
STATUS_MARK = "\x1e"
MAX_ROUNDS = 3
MAX_ITEMS = 10

MONTHS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
          "setembro", "outubro", "novembro", "dezembro"]
WEEKDAYS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]


def _fn(name: str, description: str, properties: Optional[Dict[str, Any]] = None,
        required: Optional[List[str]] = None) -> Dict[str, Any]:
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties or {}, "required": required or []},
    }}


_TICKER = {"ticker": {"type": "string", "description": "Código do ativo, ex.: PETR4, VALE3, AAPL, BTC"}}
_MONTH = {
    "mes": {"type": "integer", "description": "Mês de 1 a 12 (padrão: mês atual)"},
    "ano": {"type": "integer", "description": "Ano com 4 dígitos (padrão: ano atual)"},
}

# Cada descrição diz QUANDO usar, com exemplos de pergunta: modelos pequenos escolhem melhor
# assim do que com uma descrição só do que a ferramenta faz (evals/tools_eval.py)
TOOLS = [
    _fn("cotacao", "Preço agora e variação do dia de um ativo (ação, FII, ETF, BDR, ação americana ou "
        "criptomoeda). Use para: 'quanto está a PETR4', 'preço do bitcoin', 'a VALE3 subiu hoje'.",
        _TICKER, ["ticker"]),
    _fn("indicadores", "Indicadores fundamentalistas de UMA ação citada pelo código: P/L, P/VP, dividend yield, "
        "ROE, margem. Use para: 'qual o P/L da WEGE3', 'a TAEE11 paga bons dividendos'. Não use para explicar "
        "o que é um indicador.", _TICKER, ["ticker"]),
    _fn("resumo_do_mes", "Quanto o usuário ganhou e gastou no mês, o saldo e as categorias com mais gastos. "
        "Use para: 'quanto gastei este mês', 'sobrou dinheiro', 'em que mais gastei', 'como foi setembro'.",
        _MONTH),
    _fn("transacoes", "Total gasto (ou recebido) com um estabelecimento ou categoria. Use para: 'quanto gastei "
        "com iFood', 'gastos no mercado' (busca='mercado'), 'quanto recebi de salário' (tipo='receita').", {
            "busca": {"type": "string", "description": "Estabelecimento ou categoria citado na pergunta, ex.: ifood, "
                      "uber, mercado. Obrigatório."},
            "tipo": {"type": "string", "enum": ["despesa", "receita"], "description": "Padrão: despesa"},
            **_MONTH,
        }, ["busca"]),
    _fn("contas", "Saldo das contas bancárias e cartões do usuário. Use para: 'quanto tenho na conta', "
        "'qual meu saldo'."),
    _fn("carteira", "Investimentos do usuário: valor da carteira, lucro ou prejuízo e quais ativos ele tem. "
        "Use para: 'quanto vale minha carteira', 'meus investimentos estão no lucro', 'quais ações eu tenho'."),
    _fn("metas", "Metas financeiras do usuário (viagem, reserva de emergência...): quanto guardou e quanto falta. "
        "Use para: 'como está minha meta', 'quanto falta para minha reserva'."),
    _fn("orcamento", "Limites de gasto por categoria que o usuário definiu e quanto já usou. Use para: 'estourei "
        "o orçamento', 'quanto ainda posso gastar com lazer'.", _MONTH),
    _fn("watchlist", "Ativos que o usuário acompanha na watchlist, com preço-alvo e preço agora. Use para: "
        "'como estão os ativos que acompanho', 'algum chegou no preço-alvo'."),
    _fn("calcular", "Faz uma conta exata. Use sempre que precisar calcular: juros compostos, porcentagem, "
        "divisão, soma. Ex.: 'R$ 1.000 a 1% ao mês por 12 meses' vira expressao='1000 * 1.01 ** 12'.", {
            "expressao": {"type": "string", "description": "Conta com números, + - * / ** e parênteses. "
                          "Ponto como separador decimal: 1.01, não 1,01"},
        }, ["expressao"]),
]

STATUS_LABELS = {
    "cotacao": "cotação de {ticker}",
    "indicadores": "indicadores de {ticker}",
    "resumo_do_mes": "resumo do mês",
    "transacoes": "transações",
    "contas": "saldo das contas",
    "carteira": "carteira",
    "metas": "metas",
    "orcamento": "orçamento",
    "watchlist": "watchlist",
    "calcular": "cálculo",
}

TOOLS_PROMPT = """

DADOS DO APP: você tem ferramentas que consultam dados reais e atuais do app. Hoje é {today}.
- Pergunta sobre preço ou cotação de um ativo: use cotacao. Nunca diga que não tem acesso a
  dados em tempo real.
- Pergunta sobre o dinheiro do próprio usuário ("gastei", "recebi", "meu saldo", "minha
  carteira", "minha meta", "meu orçamento"): use a ferramenta certa antes de responder. Você
  não sabe esses números sem ela.
- Pergunta de conceito ("o que é", "como funciona", "vale a pena", "diferença entre"): responda
  direto, sem ferramenta.
- Conta (juros, porcentagem, quanto rende): use calcular em vez de fazer de cabeça. Não
  acrescente exemplos com contas ("se investisse R$ 100...") que não pediram.
- Responda só o que foi perguntado, em poucas frases, com os números exatamente como a
  ferramenta devolveu. Se ela devolver "erro", explique o problema em uma frase.
- Escreva contas e fórmulas em texto simples (1.000 × 1,01¹² = 1.126,83), nunca em LaTeX.
"""


def tools_prompt(today: Optional[date] = None) -> str:
    today = today or date.today()
    return TOOLS_PROMPT.format(
        today=f"{WEEKDAYS[today.weekday()]}, {today.day} de {MONTHS[today.month - 1]} de {today.year}")


def brl(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    sign = "-" if value < 0 else ""
    digits = 2 if abs(value) >= 1 or value == 0 else 8
    text = f"{abs(value):,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    if digits == 8:
        text = text.rstrip("0").rstrip(",")
    return f"{sign}R$ {text}"


def pct(value: Optional[float], signed: bool = True) -> Optional[str]:
    if value is None:
        return None
    text = f"{abs(value):.2f}".replace(".", ",")
    return f"{('+' if value >= 0 else '-') if signed else ''}{text}%"


def _money(value: Optional[float], currency: str) -> Optional[str]:
    if currency == "BRL":
        return brl(value)
    return None if value is None else f"{currency} {value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _month_args(args: Dict[str, Any], today: date) -> tuple:
    try:
        month = int(args.get("mes") or today.month)
        year = int(args.get("ano") or today.year)
    except (TypeError, ValueError):
        return today.year, today.month
    if not 1 <= month <= 12:
        month = today.month
    if year < 100:  # "26" -> 2026
        year += 2000
    return year, month


class Toolbox:
    """Executa as ferramentas com os agentes do app (os mesmos que as telas usam)."""

    def __init__(self, financial, personal, today: Optional[Callable[[], date]] = None):
        self.financial = financial
        self.personal = personal
        self._today = today or date.today

    def today(self) -> date:
        return self._today()

    def run(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        fn = getattr(self, f"_tool_{name}", None)
        if fn is None or name not in STATUS_LABELS:
            return {"erro": f"Ferramenta desconhecida: {name}."}
        try:
            return fn(args or {})
        except Exception as e:  # nunca derruba a conversa: o modelo explica o erro
            logger.warning("Ferramenta %s falhou: %s", name, e)
            return {"erro": str(e) or e.__class__.__name__}

    def _tool_calcular(self, args: Dict[str, Any]) -> Dict[str, Any]:
        value = safe_calc(args.get("expressao", ""))
        formatted = f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        return {"expressao": args.get("expressao"), "resultado": formatted}

    # ── Mercado ─────────────────────────────────────────────────────────

    @staticmethod
    def _ticker(args: Dict[str, Any]) -> str:
        from stonks_ai.utils.portfolio import normalize_ticker

        raw = args.get("ticker")
        ticker = normalize_ticker(str(raw or ""))
        # Modelo pequeno às vezes manda "CDB vs Tesouro Direto" ou "null": recusa sem ir à internet
        if not re.fullmatch(r"\^?[A-Z0-9]{1,6}(\.[A-Z]{1,2})?", ticker) or ticker in {"NULL", "NONE"}:
            raise ValueError(f"'{raw}' não é um código de ativo (ex.: PETR4, AAPL, BTC).")
        return ticker

    def _tool_cotacao(self, args: Dict[str, Any]) -> Dict[str, Any]:
        from stonks_ai.collectors import crypto

        ticker = self._ticker(args)
        if crypto.is_crypto(ticker):
            q = crypto.get_quote(ticker)
            return {"ativo": ticker, "nome": q.name, "preco": brl(q.price), "variacao_no_dia": pct(q.change_percent)}
        q = self.financial.get_quote(ticker)
        return {
            "ativo": q.ticker, "nome": q.name, "bolsa": q.exchange,
            "preco": _money(q.price, q.currency), "variacao_no_dia": pct(q.change_percent),
            "abertura": _money(q.open_price, q.currency), "maxima_do_dia": _money(q.high, q.currency),
            "minima_do_dia": _money(q.low, q.currency), "fechamento_anterior": _money(q.previous_close, q.currency),
        }

    def _tool_indicadores(self, args: Dict[str, Any]) -> Dict[str, Any]:
        ticker = self._ticker(args)
        f = self.financial.get_fundamentals(ticker)
        if not f:
            return {"erro": f"Sem indicadores para {ticker}."}

        def num(v: Optional[float]) -> Optional[str]:
            return None if v is None else f"{v:.2f}".replace(".", ",")

        # Múltiplos com a explicação junto: só "33,42" o modelo lia como "R$ 33,42"
        def times(v: Optional[float], of: str) -> Optional[str]:
            return None if v is None else f"{num(v)} (o preço é {num(v)} vezes {of}; não é valor em reais)"

        def frac(v: Optional[float]) -> Optional[str]:
            return None if v is None else pct(v * 100, signed=False)

        out = {
            "ativo": ticker, "nome": f.name, "setor": f.sector,
            "p_l": times(f.pe_ratio, "o lucro por ação"), "p_vp": times(f.pb_ratio, "o valor patrimonial por ação"),
            "dividend_yield_12m": frac(f.dividend_yield),
            "roe": frac(f.roe), "margem_liquida": frac(f.net_margin), "divida_patrimonio": num(f.debt_equity),
            "valor_de_mercado": _money(f.market_cap, f.currency) if f.market_cap else None,
        }
        return {k: v for k, v in out.items() if v is not None}

    def _tool_watchlist(self, args: Dict[str, Any]) -> Dict[str, Any]:
        from stonks_ai.database import db
        from stonks_ai.models.watchlist import WatchlistItem

        with db.session() as s:
            items = [(i.ticker, i.target_price) for i in s.query(WatchlistItem).order_by(WatchlistItem.added_at.desc())]
        if not items:
            return {"ativos": [], "observacao": "A watchlist está vazia."}
        rows = []
        for ticker, target in items[:MAX_ITEMS]:
            row: Dict[str, Any] = {"ativo": ticker, "preco_alvo": brl(target) if target else None}
            try:
                q = self.financial.get_quote(ticker)
                row["preco"] = _money(q.price, q.currency)
                if target:
                    row["distancia_do_alvo"] = pct((target / q.price - 1) * 100)
            except Exception:
                row["preco"] = "indisponível"
            rows.append(row)
        return {"ativos": rows}

    # ── Finanças pessoais ───────────────────────────────────────────────

    def _tool_resumo_do_mes(self, args: Dict[str, Any]) -> Dict[str, Any]:
        from stonks_ai.utils.finance_utils import get_month_summary

        today = self._today()
        year, month = _month_args(args, today)
        current = (year, month) == (today.year, today.month)
        # Mês em andamento: só até hoje (o agendado ainda não saiu), como no Início
        tomorrow = today + timedelta(days=1)
        until = datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=timezone.utc) if current else None
        s = get_month_summary(year, month, until=until)
        out = {
            "mes": f"{MONTHS[month - 1]} de {year}" + (f" (até hoje, dia {today.day})" if current else ""),
            "entrou": brl(s["total_income"]), "saiu": brl(s["total_expense"]), "saldo": brl(s["balance"]),
            "transacoes": s["transaction_count"],
            "maiores_gastos": [
                {"categoria": c["name"], "valor": brl(c["amount"]), "parte_dos_gastos": pct(c["percent"], signed=False)}
                for c in (s.get("top_categories") or [])[:5]
            ],
        }
        if not s["transaction_count"]:
            out["observacao"] = "Nenhuma transação lançada neste mês."
        return out

    def _tool_transacoes(self, args: Dict[str, Any]) -> Dict[str, Any]:
        from stonks_ai.database import db
        from stonks_ai.models.transaction import Transaction

        today = self._today()
        year, month = _month_args(args, today)
        start = datetime(year, month, 1)
        end = datetime(year, month, calendar.monthrange(year, month)[1]) + timedelta(days=1)
        end = min(end, datetime.combine(today + timedelta(days=1), datetime.min.time()))
        kind = "income" if args.get("tipo") == "receita" else "expense"
        term = str(args.get("busca") or "").strip()

        with db.session() as s:
            q = s.query(Transaction).filter(Transaction.type == kind, Transaction.date >= start, Transaction.date < end)
            if term:
                like = f"%{term}%"
                q = q.filter(or_(Transaction.description.ilike(like), Transaction.category_name.ilike(like)))
            total = q.with_entities(func.coalesce(func.sum(Transaction.amount), 0.0), func.count(Transaction.id)).one()
            rows = q.order_by(Transaction.date.desc()).limit(MAX_ITEMS).all()
            items = [{"data": t.date.strftime("%d/%m"), "descricao": t.description, "categoria": t.category_name,
                      "valor": brl(t.amount)} for t in rows]
        return {
            "periodo": f"{MONTHS[month - 1]} de {year}", "busca": term or None,
            "tipo": "receitas" if kind == "income" else "despesas",
            "total": brl(total[0]), "quantidade": total[1],
            "ultimas": items,
        }

    def _tool_contas(self, args: Dict[str, Any]) -> Dict[str, Any]:
        accounts = self.personal.list_accounts(active_only=True)
        return {
            "contas": [{"nome": a["name"], "tipo": a["account_type"], "saldo": brl(a.get("balance") or 0)}
                       for a in accounts],
            "total": brl(sum(a.get("balance") or 0 for a in accounts)),
        }

    def _tool_carteira(self, args: Dict[str, Any]) -> Dict[str, Any]:
        from stonks_ai.utils import portfolio

        o = portfolio.overview()
        t = o["totals"]
        if not t["operation_count"]:
            return {"observacao": "A carteira está vazia: nenhuma operação lançada."}
        return {
            "valor_total": brl(t["market_value"]), "investido": brl(t["invested"]),
            "resultado": brl(t["result"]), "resultado_percentual": pct(t["result_percent"]),
            "proventos_12_meses": brl(t["income_12m"]),
            "posicoes": [{
                "ativo": p["ticker"], "quantidade": p["quantity"], "valor": brl(p["market_value"]),
                "resultado": pct(p["result_percent"]), "peso": pct(p["weight"], signed=False),
            } for p in o["positions"][:MAX_ITEMS]],
        }

    def _tool_metas(self, args: Dict[str, Any]) -> Dict[str, Any]:
        goals = self.personal.list_goals(status="active")
        if not goals:
            return {"metas": [], "observacao": "Nenhuma meta ativa."}
        return {"metas": [{
            "nome": g["name"], "objetivo": brl(g["target_amount"]), "guardado": brl(g["current_amount"]),
            "falta": brl(g["remaining_amount"]), "progresso": pct(g["progress_percent"], signed=False),
            "prazo": g["deadline"][:10] if g.get("deadline") else None,
        } for g in goals[:MAX_ITEMS]]}

    def _tool_orcamento(self, args: Dict[str, Any]) -> Dict[str, Any]:
        today = self._today()
        year, month = _month_args(args, today)
        b = self.personal.get_budget_overview(year, month)
        # O percent da visão de orçamento para em 100%; aqui vale o real (130% = estourou)
        rows = [{
            "categoria": c["name"], "limite": brl(c["budget_limit"]) if c.get("budget_limit") else None,
            "gasto": brl(c["spent"]),
            "usado": pct(c["spent"] / c["budget_limit"] * 100, signed=False) if c.get("budget_limit") else None,
        } for c in b.get("categories", []) if c.get("budget_limit") or c.get("spent")]
        out: Dict[str, Any] = {"mes": f"{MONTHS[month - 1]} de {year}", "categorias": rows[:MAX_ITEMS + 5]}
        if not any(r["limite"] for r in rows):
            out["observacao"] = "Nenhum limite de orçamento definido (Orçamento, no app)."
        return out


_MONTH_TOOLS = {"resumo_do_mes", "transacoes", "orcamento"}
_LAST_MONTH = re.compile(r"m[eê]s passado|m[eê]s anterior|[uú]ltimo m[eê]s", re.I)


# ── Calculadora ─────────────────────────────────────────────────────────
# Só aritmética, pela árvore da expressão: nada de eval(), nomes ou chamadas de função.

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow,
        ast.USub: operator.neg, ast.UAdd: operator.pos}
MAX_EXPRESSION = 200


def safe_calc(expression: str) -> float:
    text = str(expression or "").strip().replace("×", "*").replace("÷", "/").replace("^", "**")
    text = text.replace("R$", "")
    # Número brasileiro: "1.000" e "1.234,56" têm ponto de milhar (mas "1.01" é decimal)
    text = re.sub(r"\b\d{1,3}(?:\.\d{3})+(?:,\d+)?\b", lambda m: m.group(0).replace(".", "").replace(",", "."), text)
    text = re.sub(r"(?<=\d),(?=\d)", ".", text)  # 1,01 -> 1.01
    if not text or len(text) > MAX_EXPRESSION:
        raise ValueError("Conta vazia ou longa demais.")

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            left, right = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Pow) and (abs(right) > 1000 or abs(left) > 1e12):
                raise ValueError("Potência grande demais.")
            return _OPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.operand))
        raise ValueError("Use só números, + - * / ** e parênteses.")

    try:
        result = ev(ast.parse(text, mode="eval"))
    except (SyntaxError, ZeroDivisionError, OverflowError) as e:
        raise ValueError(f"Não deu para calcular '{expression}': {e}")
    if isinstance(result, complex):
        raise ValueError("O resultado não é um número real.")
    return float(result)


def normalize_call(call: Dict[str, Any], question: str = "", today: Optional[date] = None) -> Dict[str, Any]:
    """Arruma o que modelos pequenos erram nos argumentos.

    - Argumentos embrulhados em {"parameters": {...}}, como o llama3.2:1b às vezes manda.
    - Mês citado na pergunta ("e em setembro?", "mês passado") que o modelo esqueceu de passar:
      sem ele, a ferramenta devolveria o mês atual.
    """
    args = call["arguments"].get("parameters")
    args = dict(args if isinstance(args, dict) else call["arguments"])
    if call["name"] in _MONTH_TOOLS and not args.get("mes") and question:
        today = today or date.today()
        lower = question.lower()
        month = next((i + 1 for i, name in enumerate(MONTHS) if re.search(rf"\b{name}\b", lower)), None)
        if month is None and _LAST_MONTH.search(question):
            month = 12 if today.month == 1 else today.month - 1
            args.setdefault("ano", today.year - 1 if today.month == 1 else today.year)
        if month:
            args["mes"] = month
            # "dezembro", perguntado em janeiro, é o do ano passado
            args.setdefault("ano", today.year - 1 if month > today.month else today.year)
    return {**call, "arguments": args}


# ── Consulta garantida de ativos ───────────────────────────────────────
# Modelos pequenos às vezes pulam a ferramenta numa pergunta de seguimento ("e a VALE3?") e
# repetem o formato da resposta anterior com um preço inventado. Ativo citado na pergunta é
# consultado pelo próprio app antes de o modelo responder (evals/tools_eval.py, casos seg-*).

_B3_TICKER = re.compile(r"\b([A-Za-z]{4}\d{1,2})\b")
_CRYPTO_NAMES = {
    "bitcoin cash": "BCH", "bitcoin": "BTC", "ethereum": "ETH", "ether": "ETH", "solana": "SOL",
    "cardano": "ADA", "dogecoin": "DOGE", "litecoin": "LTC", "chainlink": "LINK", "avalanche": "AVAX",
    "polkadot": "DOT", "tron": "TRX", "stellar": "XLM", "shiba inu": "SHIB", "cosmos": "ATOM",
    "near protocol": "NEAR", "tether": "USDT", "usd coin": "USDC", "xrp": "XRP", "ripple": "XRP",
}
_INDICATOR_WORDS = re.compile(r"p\s*/\s*l\b|p\s*/\s*vp|dividend|\bdy\b|yield|\broe\b|margem|indicador|fundament|"
                              r"endividamento|valuation|lpa\b|vpa\b", re.I)
_FOLLOW_UP = re.compile(r"\b(dela|dele|dessa|desse|desta|deste|ela|ele|essa a[cç][aã]o|esse ativo)\b", re.I)
MAX_PREFETCH = 3


def assets_in(text: str) -> List[str]:
    """Códigos da B3 e criptomoedas citados no texto, na ordem, sem repetir."""
    from stonks_ai.collectors.crypto import ASSETS

    found: List[tuple] = [(m.start(), m.group(1).upper()) for m in _B3_TICKER.finditer(text)]
    lower = text.lower()
    taken: List[tuple] = []
    for name, symbol in _CRYPTO_NAMES.items():  # "bitcoin cash" antes de "bitcoin"
        for m in re.finditer(rf"\b{re.escape(name)}\b", lower):
            if not any(a <= m.start() < b for a, b in taken):
                found.append((m.start(), symbol))
                taken.append((m.start(), m.end()))
    # Símbolo de cripto só em maiúsculas: "sol", "ada" e "link" são palavras comuns
    for m in re.finditer(r"\b([A-Z]{2,5})\b", text):
        if m.group(1) in ASSETS:
            found.append((m.start(), m.group(1)))
    out: List[str] = []
    for _, symbol in sorted(found):
        if symbol not in out:
            out.append(symbol)
    return out


def prefetch_calls(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ferramentas que o app chama sozinho para a última pergunta (cotação ou indicadores)."""
    users = [m["content"] for m in messages if m.get("role") == "user"]
    if not users:
        return []
    question = users[-1]
    assets = assets_in(question)
    if not assets and len(users) > 1 and _FOLLOW_UP.search(question):
        assets = assets_in(users[-2])  # "qual o dividend yield dela?"
    name = "indicadores" if _INDICATOR_WORDS.search(question) else "cotacao"
    from stonks_ai.collectors.crypto import is_crypto

    return [{"name": "cotacao" if is_crypto(t) else name, "arguments": {"ticker": t}} for t in assets[:MAX_PREFETCH]]


def build_convo(messages: List[Dict[str, Any]], system_prompt: str) -> List[Dict[str, Any]]:
    """Sistema + pergunta nova; a conversa anterior vai para o sistema, como contexto.

    Com as respostas anteriores como mensagens, o qwen2.5:3b copiava o formato delas sem
    chamar a ferramenta (0 de 5 perguntas de seguimento); como contexto, acerta a maioria.
    """
    *history, last = messages
    if history:
        lines = "\n".join(f"{'Usuário' if m['role'] == 'user' else 'Assistente'}: {m['content']}" for m in history)
        system_prompt += ("\n\nCONVERSA ATÉ AGORA (para entender a pergunta nova; os números dela podem estar "
                          f"desatualizados e não valem para outro ativo ou outro mês):\n{lines}")
    return [{"role": "system", "content": system_prompt}, last]


def _status(name: str, args: Dict[str, Any]) -> str:
    label = STATUS_LABELS.get(name, name)
    try:
        label = label.format(ticker=str(args.get("ticker") or "").upper())
    except (KeyError, IndexError):
        pass
    return f"{STATUS_MARK}{label}{STATUS_MARK}"


async def chat_with_tools(llm, messages: List[Dict[str, Any]], system_prompt: str,
                          toolbox: Toolbox, max_rounds: int = MAX_ROUNDS) -> AsyncIterator[str]:
    """Conversa em streaming: o texto vai saindo e cada ferramenta usada vira uma linha de status.

    Ativos citados na pergunta são consultados antes (prefetch_calls); depois, até max_rounds
    rodadas em que o modelo pede ferramentas; na última, ele responde sem elas.
    """
    convo = build_convo(messages, system_prompt)
    fetched: List[Dict[str, Any]] = []

    def run_calls(calls: List[Dict[str, Any]]):
        convo.append({"role": "assistant", "content": "", "tool_calls": [
            {"function": {"name": c["name"], "arguments": c["arguments"]}} for c in calls]})
        for c in calls:
            result = toolbox.run(c["name"], c["arguments"])
            fetched.append({"ferramenta": c["name"], **result})
            convo.append({"role": "tool", "content": json.dumps(result, ensure_ascii=False), "tool_name": c["name"]})

    forced = prefetch_calls(messages)
    if forced:
        for c in forced:
            yield _status(c["name"], c["arguments"])
        run_calls(forced)

    for round_no in range(max_rounds + 1):
        use_tools = round_no < max_rounds
        calls: List[Dict[str, Any]] = []
        try:
            async for event in llm.stream_chat(convo, tools=TOOLS if use_tools else None):
                if "content" in event and not calls:
                    yield event["content"]
                calls.extend(event.get("tool_calls") or [])
        except LLMError as e:
            if e.code != "LLM-007" or round_no:
                raise
            # Modelo sem ferramentas (ex.: gemma3): os dados já consultados vão no texto do sistema
            logger.info("Modelo sem ferramentas; respondendo sem elas.")
            plain = build_convo(messages, system_prompt)
            if fetched:
                plain[0]["content"] += "\n\nDADOS CONSULTADOS AGORA NO APP:\n" + json.dumps(fetched, ensure_ascii=False)
            async for event in llm.stream_chat(plain):
                if "content" in event:
                    yield event["content"]
            return
        if not calls:
            return
        calls = [normalize_call(c, messages[-1]["content"], toolbox.today()) for c in calls]
        # Não repete o que o app já consultou nesta pergunta
        done = {(c["name"], json.dumps(c["arguments"], sort_keys=True)) for c in forced}
        calls = [c for c in calls if (c["name"], json.dumps(c["arguments"], sort_keys=True)) not in done] or calls
        for c in calls:
            yield _status(c["name"], c["arguments"])
        run_calls(calls)
