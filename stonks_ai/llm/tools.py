"""
Ferramentas da IA: o chat consulta dados reais do app em vez de responder de memória (ADR 026).

O modelo recebe a lista de ferramentas (TOOLS), decide se precisa de alguma, o app executa
(Toolbox) e devolve o resultado; o modelo então responde com os números de verdade.

Nenhuma ferramenta muda dados. As de lançamento (WRITE_TOOLS: transação, aporte em meta,
watchlist) só montam uma proposta; a tela mostra com Confirmar e Cancelar, e quem grava é a
rota de sempre do app quando o usuário confirma (ADR 027).

Os resultados são curtos e já formatados ("R$ 1.234,56", "+1,5%"): modelos pequenos erram
menos repetindo um número pronto do que formatando um float.
"""

import ast
import calendar
import json
import operator
import logging
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

from sqlalchemy import func, or_

from stonks_ai.llm.base import LLMError

logger = logging.getLogger("stonks_ai.llm.tools")

# Marca uma linha de status no texto do chat ("Consultando cotação de PETR4"); a tela tira
# essas linhas da resposta e mostra à parte (desktop/frontend/js/chat.js)
STATUS_MARK = "\x1e"
# Marca uma proposta de lançamento (JSON entre duas marcas); a tela mostra Confirmar e Cancelar
PROPOSAL_MARK = "\x1d"
WRITE_TOOLS = {"lancar_transacao", "aportar_meta", "adicionar_watchlist"}
PENDING = "Proposta mostrada na tela. AINDA NÃO FOI LANÇADO: o usuário precisa clicar em Confirmar."
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
    _fn("lancar_transacao", "Prepara o lançamento de um gasto ou de uma receita para o usuário confirmar na tela. "
        "Use quando ele contar um gasto ou um recebimento, ou pedir para lançar, registrar ou anotar: 'gastei 45 no "
        "iFood', 'lança 120 de conta de luz ontem', 'recebi 3.500 de salário' e 'anota um pix de 200 que recebi' "
        "(tipo=receita). Não use para perguntas como 'quanto gastei'.", {
            "descricao": {"type": "string", "description": "Onde ou com o quê, ex.: iFood, conta de luz, salário"},
            "valor": {"type": "number", "description": "Valor em reais, ex.: 45.9"},
            "tipo": {"type": "string", "enum": ["despesa", "receita"], "description": "Padrão: despesa"},
            "data": {"type": "string", "description": "AAAA-MM-DD, 'hoje' ou 'ontem'. Só se o usuário disser a data"},
            "categoria": {"type": "string", "description": "Só se o usuário disser a categoria"},
            "conta": {"type": "string", "description": "Só se o usuário disser a conta ou o cartão, ex.: Nubank"},
        }, ["descricao", "valor"]),
    _fn("aportar_meta", "Prepara um aporte (dinheiro guardado) numa META do usuário, para ele confirmar na tela. "
        "Use só quando ele citar a meta: 'guardei 300 na meta da viagem', 'coloca 100 na reserva de emergência'. "
        "Salário ou pix recebido não é meta: é lancar_transacao.", {
            "meta": {"type": "string", "description": "Nome da meta, ex.: viagem, reserva"},
            "valor": {"type": "number", "description": "Valor em reais"},
        }, ["meta", "valor"]),
    _fn("adicionar_watchlist", "Prepara a inclusão de UM ativo novo, citado pelo código, na watchlist, com "
        "preço-alvo opcional, para o usuário confirmar na tela. Use só quando ele pedir para adicionar: 'adiciona "
        "a WEGE3 na watchlist', 'quero acompanhar a PETR4 e ser avisado em R$ 35'. Para ver como estão os ativos "
        "que ele já acompanha, use watchlist.", {
            **_TICKER,
            "preco_alvo": {"type": "number", "description": "Preço-alvo, só se o usuário disser"},
        }, ["ticker"]),
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
    "lancar_transacao": "lançamento",
    "aportar_meta": "aporte na meta",
    "adicionar_watchlist": "watchlist",
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
- Pedido para lançar, registrar ou anotar um gasto ou receita: use lancar_transacao. Para guardar
  dinheiro numa meta: aportar_meta. Para acompanhar um ativo: adicionar_watchlist. Elas só
  preparam: diga em uma frase o que preparou e que falta confirmar no botão abaixo. Nunca diga
  que já lançou.
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


def _plain(text: Any) -> str:
    """Sem acento, minúsculo: para comparar o nome que o modelo mandou com o do app."""
    return unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower().strip()


def _pick(term: Any, names: List[str]) -> List[str]:
    """Nomes do app que combinam com o termo: igual primeiro, depois um contido no outro."""
    t = _plain(term)
    if not t:
        return []
    exact = [n for n in names if _plain(n) == t]
    return exact or [n for n in names if t in _plain(n) or (_plain(n) and _plain(n) in t)]


def _amount(raw: Any) -> float:
    """Valor positivo em reais: aceita 45.9, "45,90", "R$ 1.200,00" e -45 (o sinal vem do tipo)."""
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        value = float(raw)
    else:
        text = str(raw or "").replace("R$", "").strip()
        text = re.sub(r"\b\d{1,3}(?:\.\d{3})+(?:,\d+)?\b",
                      lambda m: m.group(0).replace(".", "").replace(",", "."), text).replace(",", ".")
        try:
            value = float(text)
        except ValueError:
            raise ValueError(f"'{raw}' não é um valor em reais.")
    value = round(abs(value), 2)
    if not 0 < value < 1e9:
        raise ValueError("O valor precisa ser maior que zero.")
    return value


def _date_arg(raw: Any, today: date) -> date:
    text = _plain(raw)
    if text in ("", "hoje", "none", "null"):
        return today
    relative = {"ontem": 1, "anteontem": 2}
    if text in relative:
        return today - timedelta(days=relative[text])
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})", text)
    if m:
        try:
            return date(today.year, int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass
    raise ValueError(f"Data '{raw}' não reconhecida (use AAAA-MM-DD).")


def _propose(kind: str, title: str, rows: List[list], body: Dict[str, Any], done: str,
             summary: str, **extra: Any) -> Dict[str, Any]:
    """Resultado de uma ferramenta de lançamento: o resumo vai para o modelo; a proposta, para a tela.

    rows: [rótulo, valor, moeda]; com moeda, a tela formata o valor (e esconde, se o usuário
    estiver com os valores ocultos).
    """
    return {"situacao": PENDING, "resumo": summary, "_proposta": {
        "tipo": kind, "titulo": title, "linhas": rows, "corpo": body, "feito": done, **extra}}


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
        self.question = ""  # a pergunta em andamento (chat_with_tools); ajuda a completar lançamentos

    def today(self) -> date:
        return self._today()

    def run(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Resultado para o modelo; nas de lançamento, com a proposta para a tela em "_proposta"."""
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

    # ── Lançamentos (só propõem; quem grava é a tela, quando o usuário confirma) ──

    def _tool_lancar_transacao(self, args: Dict[str, Any]) -> Dict[str, Any]:
        desc = str(args.get("descricao") or "").strip()[:200]
        # Seguimento ("lança mais 38 de hoje") às vezes vem com a data no lugar da descrição
        if _plain(desc) in ("", "hoje", "ontem", "anteontem", "gasto", "despesa", "receita"):
            raise ValueError("Falta a descrição: onde foi o gasto ou de onde veio a receita.")
        if desc.islower():  # "salario" -> "Salario"; "iFood" fica como está
            desc = desc[0].upper() + desc[1:]
        value = _amount(args.get("valor"))
        kind = "income" if _plain(args.get("tipo")) in ("receita", "income", "entrada") else "expense"
        when = _date_arg(args.get("data"), self._today())

        found = _pick(args.get("categoria"), [c["name"] for c in self.personal.list_categories()])
        category = found[0] if found else self.personal.categorizer.categorize(desc)[1]
        account = None
        accounts = self.personal.list_accounts(active_only=True)
        wanted = args.get("conta")
        if not wanted:  # "recebi 3.500 no Nubank": o modelo nem sempre passa a conta que a frase cita
            asked = _plain(self.question)
            wanted = next((a["name"] for a in accounts
                           if _plain(a["name"]) and re.search(rf"\b{re.escape(_plain(a['name']))}\b", asked)), None)
        if wanted:
            names = _pick(wanted, [a["name"] for a in accounts])
            if len(names) != 1:
                raise ValueError(f"Conta '{wanted}' não encontrada. Contas: "
                                 f"{', '.join(a['name'] for a in accounts) or 'nenhuma cadastrada'}.")
            account = next(a for a in accounts if a["name"] == names[0])

        label = "receita" if kind == "income" else "despesa"
        rows = [["Descrição", desc], ["Valor", value, "BRL"], ["Data", when.strftime("%d/%m/%Y")],
                ["Categoria", category + ("" if found else " (automática)")]]
        if account:
            rows.append(["Conta", account["name"]])
        return _propose(
            "transacao", f"Lançar {label}", rows,
            {"description": desc, "amount": value, "type": kind, "date": when.isoformat(),
             "category_name": category, "account_id": account["id"] if account else None},
            done=f"{label.capitalize()} lançada.",
            summary=f"{label} de {brl(value)}, {desc}, em {when.strftime('%d/%m/%Y')}, categoria {category}"
                    + (f", conta {account['name']}" if account else ""))

    def _tool_aportar_meta(self, args: Dict[str, Any]) -> Dict[str, Any]:
        value = _amount(args.get("valor"))
        goals = self.personal.list_goals(status="active")
        if not goals:
            raise ValueError("Não há metas ativas. Crie uma na tela Metas.")
        names = _pick(args.get("meta"), [g["name"] for g in goals])
        # "coloca 100 na minha meta", e só existe uma. Um nome qualquer ("salário") não cai nela.
        if not names and len(goals) == 1 and (not _plain(args.get("meta")) or "meta" in _plain(args.get("meta"))):
            names = [goals[0]["name"]]
        if len(names) != 1:
            which = "Mais de uma meta combina" if names else f"Meta '{args.get('meta')}' não encontrada"
            raise ValueError(f"{which}. Metas ativas: {', '.join(g['name'] for g in goals)}.")
        goal = next(g for g in goals if g["name"] == names[0])
        after = goal["current_amount"] + value
        return _propose(
            "meta", "Aportar na meta",
            [["Meta", goal["name"]], ["Aporte", value, "BRL"], ["Guardado depois", after, "BRL"],
             ["Objetivo", goal["target_amount"], "BRL"]],
            {"amount": value}, id=goal["id"],
            done="Aporte registrado." + (" Meta concluída!" if after >= goal["target_amount"] else ""),
            summary=f"aporte de {brl(value)} na meta {goal['name']} (fica com {brl(after)} de "
                    f"{brl(goal['target_amount'])})")

    def _tool_adicionar_watchlist(self, args: Dict[str, Any]) -> Dict[str, Any]:
        from stonks_ai.collectors import crypto
        from stonks_ai.database import db
        from stonks_ai.models.watchlist import WatchlistItem

        ticker = self._ticker(args)
        if crypto.is_crypto(ticker):
            raise ValueError("A watchlist ainda não acompanha criptomoedas.")
        with db.session() as s:
            if s.query(WatchlistItem).filter(WatchlistItem.ticker == ticker).first():
                raise ValueError(f"{ticker} já está na watchlist.")
        q = self.financial.get_quote(ticker)  # confirma que o ativo existe antes de propor
        target = _amount(args["preco_alvo"]) if args.get("preco_alvo") not in (None, "", 0) else None
        rows = [["Ativo", f"{ticker} — {q.name}" if q.name else ticker], ["Preço agora", q.price, q.currency]]
        rows.append(["Preço-alvo", target, q.currency] if target else ["Preço-alvo", "sem alvo"])
        return _propose(
            "watchlist", "Adicionar à watchlist", rows, {"ticker": ticker, "target_price": target},
            done=f"{ticker} adicionada à watchlist.",
            summary=f"{ticker} na watchlist" + (f" com preço-alvo de {_money(target, q.currency)}" if target else ""))


_MONTH_TOOLS = {"resumo_do_mes", "transacoes", "orcamento"}
_LAST_MONTH = re.compile(r"m[eê]s passado|m[eê]s anterior|[uú]ltimo m[eê]s", re.I)
_RECEIVED = re.compile(r"\b(recebi|recebemos|ganhei|caiu|entrou)\b", re.I)
_DATE_WORDS = re.compile(r"ontem|\bdia\s+\d|\d{1,2}/\d{1,2}|\d{4}-\d{2}|segunda|ter[cç]a|quarta|quinta|sexta|"
                         r"s[aá]bado|domingo|" + "|".join(MONTHS), re.I)


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
    - Data de lançamento que a pergunta não cita: modelo pequeno inventa uma do ano em que foi
      treinado; sem data na pergunta, o lançamento é de hoje.
    - "Recebi 3.500 de salário" vira aporte numa meta "salário" no qwen2.5:3b; recebimento sem
      falar de meta é lançamento de receita.
    """
    args = call["arguments"].get("parameters")
    args = dict(args if isinstance(args, dict) else call["arguments"])
    if call["name"] == "aportar_meta" and _RECEIVED.search(question) and not re.search(r"\bmeta", question, re.I):
        call = {**call, "name": "lancar_transacao"}
        args = {"descricao": args.get("meta") or "Recebimento", "valor": args.get("valor"), "tipo": "receita"}
    if call["name"] == "lancar_transacao" and question and not _DATE_WORDS.search(question):
        args.pop("data", None)
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
_WATCHLIST_WORDS = re.compile(r"watch\s?list|acompanha", re.I)
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
    if _WATCHLIST_WORDS.search(question):  # "adiciona a WEGE3 na watchlist": é pedido, não pergunta
        return []
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


def _proposal(p: Dict[str, Any]) -> str:
    return f"{PROPOSAL_MARK}{json.dumps(p, ensure_ascii=False)}{PROPOSAL_MARK}"


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
    rodadas em que o modelo pede ferramentas; na última, ele responde sem elas. Propostas de
    lançamento saem entre PROPOSAL_MARK, cada uma uma vez só.
    """
    convo = build_convo(messages, system_prompt)
    fetched: List[Dict[str, Any]] = []
    proposed: set = set()
    toolbox.question = messages[-1]["content"]

    def run_calls(calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        convo.append({"role": "assistant", "content": "", "tool_calls": [
            {"function": {"name": c["name"], "arguments": c["arguments"]}} for c in calls]})
        proposals = []
        for c in calls:
            result = toolbox.run(c["name"], c["arguments"])
            proposal = result.pop("_proposta", None)
            if proposal:
                key = json.dumps(proposal, sort_keys=True, ensure_ascii=False)
                if key in proposed:  # o modelo pediu de novo na rodada seguinte
                    result = {"situacao": "Essa proposta já está na tela, esperando o usuário confirmar."}
                else:
                    proposed.add(key)
                    proposals.append(proposal)
            fetched.append({"ferramenta": c["name"], **result})
            convo.append({"role": "tool", "content": json.dumps(result, ensure_ascii=False), "tool_name": c["name"]})
        return proposals

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
            if c["name"] not in WRITE_TOOLS:  # lançamento aparece como proposta, não como consulta
                yield _status(c["name"], c["arguments"])
        for p in run_calls(calls):
            yield _proposal(p)
