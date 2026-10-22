"""Testes das ferramentas do chat (ADR 026): o que cada uma devolve e a conversa em rodadas."""

import asyncio
import json
from datetime import date, datetime
from types import SimpleNamespace

import pytest

from stonks_ai.database import db
from stonks_ai.llm.base import LLMError
from stonks_ai.llm.tools import (PROPOSAL_MARK, STATUS_MARK, TOOLS, Toolbox, assets_in, brl, build_convo,
                                 chat_with_tools, normalize_call, pct, prefetch_calls, tools_prompt)
from stonks_ai.models.transaction import Transaction

TODAY = date(2026, 10, 21)


class FakeFinancial:
    def get_quote(self, ticker):
        if ticker == "XXXX3":
            raise RuntimeError("Ticker 'XXXX3' não encontrado na B3.")
        return SimpleNamespace(ticker=ticker, name="Petróleo Brasileiro", exchange="B3", price=58.21,
                               change_percent=0.36, open_price=57.9, high=58.5, low=57.7, previous_close=58.0,
                               currency="BRL")


class FakePersonal:
    categorizer = SimpleNamespace(categorize=lambda d: (1, "Alimentação") if "ifood" in d.lower() else (None, "Outros"))

    def list_accounts(self, active_only=True):
        return [{"id": 1, "name": "Nubank", "account_type": "checking", "balance": 1500.5},
                {"id": 2, "name": "Carteira", "account_type": "cash", "balance": 80}]

    def list_categories(self):
        return [{"name": n} for n in ("Alimentação", "Transporte", "Saúde", "Salário", "Outros")]

    def list_goals(self, status="active"):
        return [{"id": 7, "name": "Viagem", "target_amount": 5000, "current_amount": 1250, "remaining_amount": 3750,
                 "progress_percent": 25.0, "deadline": "2027-07-01T00:00:00"}]

    def get_budget_overview(self, year, month):
        return {"categories": [
            {"name": "Lazer", "budget_limit": 300.0, "spent": 390.0, "percent": 100},
            {"name": "Saúde", "budget_limit": None, "spent": 0},
        ]}


@pytest.fixture
def toolbox():
    return Toolbox(FakeFinancial(), FakePersonal(), today=lambda: TODAY)


def add_tx(day, desc, amount, kind="expense", category="Alimentação"):
    with db.session() as s:
        s.add(Transaction(description=desc, amount=amount, type=kind, category_name=category, date=datetime(*day)))


def test_formats():
    assert brl(1234.5) == "R$ 1.234,50"
    assert brl(-80) == "-R$ 80,00"
    assert brl(0.00002567) == "R$ 0,00002567"
    assert pct(0.36) == "+0,36%" and pct(-1.5) == "-1,50%" and pct(25, signed=False) == "25,00%"


def test_every_tool_has_a_runner_and_status(toolbox):
    for t in TOOLS:
        assert hasattr(toolbox, f"_tool_{t['function']['name']}")
    assert "erro" in toolbox.run("apagar_tudo", {})


def test_quote_and_unknown_ticker(toolbox):
    q = toolbox.run("cotacao", {"ticker": "petr4"})
    assert q["preco"] == "R$ 58,21" and q["variacao_no_dia"] == "+0,36%"
    assert "não encontrado" in toolbox.run("cotacao", {"ticker": "XXXX3"})["erro"]
    assert "erro" in toolbox.run("cotacao", {})
    for junk in ("CDB vs Tesouro Direto", "null", None, "P/L"):
        assert "não é um código" in toolbox.run("indicadores", {"ticker": junk})["erro"]
    assert toolbox.run("cotacao", {"ticker": "aapl"})["ativo"] == "AAPL"


def test_month_summary_stops_today(toolbox):
    add_tx((2026, 10, 5), "Salário", 5000, "income", "Salário")
    add_tx((2026, 10, 10), "IFOOD *RESTAURANTE", 60)
    add_tx((2026, 10, 25), "Aluguel agendado", 1500, category="Moradia")   # depois de hoje
    r = toolbox.run("resumo_do_mes", {})
    assert r["entrou"] == "R$ 5.000,00" and r["saiu"] == "R$ 60,00"
    assert "até hoje, dia 21" in r["mes"]


def test_transactions_search_by_text_and_month(toolbox):
    add_tx((2026, 9, 3), "UBER *TRIP", 25, category="Transporte")
    add_tx((2026, 9, 9), "Uber Eats", 40)
    add_tx((2026, 10, 2), "UBER *TRIP", 18, category="Transporte")
    r = toolbox.run("transacoes", {"busca": "uber", "mes": 9, "ano": 2026})
    assert r["total"] == "R$ 65,00" and r["quantidade"] == 2
    assert toolbox.run("transacoes", {"busca": "transporte"})["total"] == "R$ 18,00"   # pela categoria, mês atual


def test_accounts_goals_and_budget(toolbox):
    assert toolbox.run("contas", {})["total"] == "R$ 1.580,50"
    assert toolbox.run("metas", {})["metas"][0]["falta"] == "R$ 3.750,00"
    lazer = toolbox.run("orcamento", {})["categorias"][0]
    assert lazer["usado"] == "130,00%"                       # estourado, não "100%"


def test_tools_prompt_has_today():
    assert "quarta-feira, 21 de outubro de 2026" in tools_prompt(TODAY)


class FakeLLM:
    """Rodada 1 pede a cotação; rodada 2 responde com o que a ferramenta devolveu."""

    def __init__(self, supports_tools=True):
        self.supports_tools = supports_tools
        self.calls = []

    async def stream_chat(self, messages, tools=None):
        self.calls.append((list(messages), tools))
        if tools and not self.supports_tools:
            raise LLMError("LLM-007", "sem ferramentas")
        if tools and messages[-1]["role"] == "user":
            yield {"tool_calls": [{"name": "cotacao", "arguments": {"ticker": "PETR4"}}]}
            return
        last = messages[-1]
        text = f"A PETR4 está em {json.loads(last['content'])['preco']}." if last["role"] == "tool" else "Olá!"
        for word in text.split(" "):
            yield {"content": word + " "}


def collect(gen):
    async def run():
        return [part async for part in gen]
    return asyncio.run(run())


def test_model_asks_for_the_tool_and_answers_with_real_numbers(toolbox):
    llm = FakeLLM()
    # Sem código na pergunta: quem decide consultar é o modelo
    parts = collect(chat_with_tools(llm, [{"role": "user", "content": "Quanto está a ação da Petrobras?"}], "sys", toolbox))
    text = "".join(parts)
    assert f"{STATUS_MARK}cotação de PETR4{STATUS_MARK}" in text
    assert "R$ 58,21" in text
    tool_msg = llm.calls[1][0][-1]
    assert tool_msg["role"] == "tool" and tool_msg["tool_name"] == "cotacao"


def test_asset_in_the_question_is_fetched_before_the_model(toolbox):
    llm = FakeLLM()
    text = "".join(collect(chat_with_tools(llm, [{"role": "user", "content": "e a petr4?"}], "sys", toolbox)))
    assert "R$ 58,21" in text
    assert len(llm.calls) == 1                                # o modelo já recebe o resultado
    assert llm.calls[0][0][-1]["role"] == "tool"


def test_assets_and_follow_ups():
    assert assets_in("Compare PETR4 e vale3") == ["PETR4", "VALE3"]
    assert assets_in("bitcoin cash ou bitcoin? e SOL") == ["BCH", "BTC", "SOL"]
    assert assets_in("o sol está forte, vale a pena guardar dinheiro?") == []
    history = [{"role": "user", "content": "Quanto está a ITSA4?"}, {"role": "assistant", "content": "R$ 15,80"}]
    follow = prefetch_calls([*history, {"role": "user", "content": "Qual o dividend yield dela?"}])
    assert follow == [{"name": "indicadores", "arguments": {"ticker": "ITSA4"}}]
    assert prefetch_calls([*history, {"role": "user", "content": "O que é dividend yield?"}]) == []
    assert prefetch_calls([{"role": "user", "content": "P/L da WEGE3 e preço do bitcoin"}]) == [
        {"name": "indicadores", "arguments": {"ticker": "WEGE3"}}, {"name": "cotacao", "arguments": {"ticker": "BTC"}}]


def test_history_goes_to_the_system_prompt():
    convo = build_convo([{"role": "user", "content": "Quanto gastei?"}, {"role": "assistant", "content": "R$ 10"},
                         {"role": "user", "content": "E em setembro?"}], "sys")
    assert [m["role"] for m in convo] == ["system", "user"]
    assert "Assistente: R$ 10" in convo[0]["content"] and convo[1]["content"] == "E em setembro?"


def test_month_named_in_the_question_is_filled_in():
    oct21 = date(2026, 10, 21)
    call = normalize_call({"name": "resumo_do_mes", "arguments": {}}, "E em setembro?", oct21)
    assert call["arguments"] == {"mes": 9, "ano": 2026}
    jan = date(2027, 1, 10)
    assert normalize_call({"name": "transacoes", "arguments": {"busca": "uber"}}, "uber no mês passado", jan)[
        "arguments"] == {"busca": "uber", "mes": 12, "ano": 2026}
    assert normalize_call({"name": "resumo_do_mes", "arguments": {"parameters": {"mes": 3}}}, "março", oct21)[
        "arguments"] == {"mes": 3}


def test_model_without_tools_still_answers(toolbox):
    llm = FakeLLM(supports_tools=False)
    parts = collect(chat_with_tools(llm, [{"role": "user", "content": "Oi"}], "sys", toolbox))
    assert "".join(parts).strip() == "Olá!"


def test_rounds_are_limited(toolbox):
    class Looping(FakeLLM):
        async def stream_chat(self, messages, tools=None):
            self.calls.append((messages, tools))
            if tools:
                yield {"tool_calls": [{"name": "contas", "arguments": {}}]}
            else:
                yield {"content": "fim"}

    llm = Looping()
    text = "".join(collect(chat_with_tools(llm, [{"role": "user", "content": "?"}], "sys", toolbox, max_rounds=2)))
    assert text.endswith("fim")
    assert [t is not None for _, t in llm.calls] == [True, True, False]   # a última rodada é sem ferramentas


def test_chat_route_uses_tools(monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    import desktop.api as api
    from desktop.routes import assistant

    llm = FakeLLM()
    llm.is_available = lambda: True
    monkeypatch.setattr(assistant, "financial_agent", lambda: SimpleNamespace(llm=llm, get_quote=FakeFinancial().get_quote))
    monkeypatch.setattr(assistant, "personal_agent", lambda: FakePersonal())
    with TestClient(api.app, base_url="http://127.0.0.1") as c:
        r = c.post("/api/chat", json={"messages": [{"role": "user", "content": "Quanto está a PETR4?"}]})
    assert r.status_code == 200
    assert "R$ 58,21" in r.text and STATUS_MARK in r.text
    assert "Hoje é" in llm.calls[0][0][0]["content"]          # o prompt de sistema tem a data


def test_calculator_is_exact_and_safe(toolbox):
    from stonks_ai.llm.tools import safe_calc

    assert toolbox.run("calcular", {"expressao": "1000 * 1.01 ** 12"})["resultado"] == "1.126,83"
    assert safe_calc("1.000 * 1,01 ^ 12") == pytest.approx(1126.825, abs=0.001)   # "1.000" é mil
    assert safe_calc("1.234,56 + 0.5") == pytest.approx(1235.06)
    assert safe_calc("2340 * 15 / 100") == 351
    assert safe_calc("(5000 - 2340) / 5000 * 100") == pytest.approx(53.2)
    for bad in ("__import__('os').system('dir')", "open('x')", "a + 1", "9 ** 9999", "1 / 0", "", "x" * 300):
        assert "erro" in toolbox.run("calcular", {"expressao": bad}), bad


# ── Lançamentos pelo chat (ADR 027): a IA só propõe, a tela grava ao confirmar ──

def test_transaction_is_only_proposed(toolbox):
    r = toolbox.run("lancar_transacao", {"descricao": "iFood", "valor": "45,90"})
    p = r.pop("_proposta")
    assert "NÃO FOI LANÇADO" in r["situacao"] and "R$ 45,90" in r["resumo"]
    assert p["tipo"] == "transacao" and p["titulo"] == "Lançar despesa"
    assert p["corpo"] == {"description": "iFood", "amount": 45.9, "type": "expense", "date": "2026-10-21",
                          "category_name": "Alimentação", "account_id": None}
    assert ["Categoria", "Alimentação (automática)"] in p["linhas"]
    with db.session() as s:
        assert s.query(Transaction).count() == 0          # nada gravado sem o usuário confirmar


def test_transaction_arguments_are_cleaned_up(toolbox):
    p = toolbox.run("lancar_transacao", {"descricao": "Salário", "valor": -3200, "tipo": "receita", "data": "ontem",
                                         "categoria": "salario", "conta": "nubank"})["_proposta"]
    assert p["corpo"]["amount"] == 3200 and p["corpo"]["type"] == "income" and p["corpo"]["date"] == "2026-10-20"
    assert p["corpo"]["category_name"] == "Salário" and p["corpo"]["account_id"] == 1
    assert toolbox.run("lancar_transacao", {"descricao": "x", "valor": "R$ 1.200,50", "data": "05/10"}
                       )["_proposta"]["corpo"]["amount"] == 1200.5
    assert "Conta 'Itaú' não encontrada. Contas: Nubank, Carteira" in toolbox.run(
        "lancar_transacao", {"descricao": "x", "valor": 10, "conta": "Itaú"})["erro"]
    assert "maior que zero" in toolbox.run("lancar_transacao", {"descricao": "x", "valor": 0})["erro"]
    assert "Falta a descrição" in toolbox.run("lancar_transacao", {"descricao": "hoje", "valor": 38})["erro"]
    # Conta citada na frase, mas não nos argumentos; descrição toda em minúsculas ganha maiúscula
    toolbox.question = "Recebi 3.500 de salário no nubank"
    p = toolbox.run("lancar_transacao", {"descricao": "salario", "valor": 3500, "tipo": "receita"})["_proposta"]
    assert p["corpo"]["account_id"] == 1 and p["corpo"]["description"] == "Salario"
    assert "não reconhecida" in toolbox.run("lancar_transacao", {"descricao": "x", "valor": 1, "data": "amanhã cedo"})["erro"]


def test_goal_contribution_is_proposed_by_name(toolbox):
    p = toolbox.run("aportar_meta", {"meta": "viagem", "valor": 300})["_proposta"]
    assert p["tipo"] == "meta" and p["id"] == 7 and p["corpo"] == {"amount": 300}
    assert ["Guardado depois", 1550, "BRL"] in p["linhas"]
    # Só uma meta ativa: "minha meta" é ela
    assert toolbox.run("aportar_meta", {"meta": "minha meta", "valor": 10})["_proposta"]["id"] == 7
    assert "não encontrada" in toolbox.run("aportar_meta", {"meta": "salário", "valor": 10})["erro"]
    toolbox.personal.list_goals = lambda status="active": [
        {"id": 1, "name": "Viagem", "target_amount": 1, "current_amount": 0},
        {"id": 2, "name": "Reserva", "target_amount": 1, "current_amount": 0}]
    assert "Metas ativas: Viagem, Reserva" in toolbox.run("aportar_meta", {"meta": "carro", "valor": 10})["erro"]


def test_watchlist_proposal_checks_the_asset(toolbox):
    from stonks_ai.models.watchlist import WatchlistItem

    p = toolbox.run("adicionar_watchlist", {"ticker": "wege3", "preco_alvo": 35})["_proposta"]
    assert p["corpo"] == {"ticker": "WEGE3", "target_price": 35} and ["Preço agora", 58.21, "BRL"] in p["linhas"]
    assert "criptomoedas" in toolbox.run("adicionar_watchlist", {"ticker": "BTC"})["erro"]
    assert "não encontrado" in toolbox.run("adicionar_watchlist", {"ticker": "XXXX3"})["erro"]
    with db.session() as s:
        s.add(WatchlistItem(ticker="WEGE3", exchange="B3"))
    assert "já está na watchlist" in toolbox.run("adicionar_watchlist", {"ticker": "WEGE3"})["erro"]


def test_invented_date_is_dropped():
    call = {"name": "lancar_transacao", "arguments": {"descricao": "iFood", "valor": 45, "data": "2023-10-21"}}
    assert "data" not in normalize_call(call, "gastei 45 no ifood", TODAY)["arguments"]
    assert normalize_call(call, "gastei 45 no ifood dia 3", TODAY)["arguments"]["data"] == "2023-10-21"
    # Recebimento que o modelo mandou como aporte em meta
    fixed = normalize_call({"name": "aportar_meta", "arguments": {"meta": "salário", "valor": 3500}},
                           "Recebi 3.500 de salário", TODAY)
    assert fixed == {"name": "lancar_transacao", "arguments": {"descricao": "salário", "valor": 3500, "tipo": "receita"}}
    kept = {"name": "aportar_meta", "arguments": {"meta": "viagem", "valor": 300}}
    assert normalize_call(kept, "recebi 300 de bônus e coloquei na meta da viagem", TODAY) == kept
    # Pedido de watchlist não dispara a consulta automática de cotação
    assert prefetch_calls([{"role": "user", "content": "adiciona a WEGE3 na watchlist"}]) == []


class ProposingLLM:
    """Pede o lançamento duas vezes (o modelo repete) e depois responde."""

    def __init__(self):
        self.tool_results = []

    async def stream_chat(self, messages, tools=None):
        if messages[-1]["role"] == "tool":
            self.tool_results.append(json.loads(messages[-1]["content"]))
        if tools and len(self.tool_results) < 2:
            yield {"tool_calls": [{"name": "lancar_transacao", "arguments": {"descricao": "iFood", "valor": 45}}]}
            return
        yield {"content": "Preparei o lançamento: é só confirmar abaixo."}


def test_chat_sends_each_proposal_once(toolbox):
    llm = ProposingLLM()
    text = "".join(collect(chat_with_tools(llm, [{"role": "user", "content": "gastei 45 no ifood"}], "sys", toolbox)))
    assert text.count(PROPOSAL_MARK) == 2 and STATUS_MARK not in text   # uma proposta, sem "Consultei"
    proposal = json.loads(text.split(PROPOSAL_MARK)[1])
    assert proposal["corpo"]["amount"] == 45 and "_proposta" not in llm.tool_results[0]
    assert "já está na tela" in llm.tool_results[1]["situacao"]
    assert text.endswith("é só confirmar abaixo.")
