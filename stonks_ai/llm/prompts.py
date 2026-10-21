"""
Templates de prompt para os agentes de IA do Stonks AI.

Contém prompts especializados para análise financeira.
"""

FINANCIAL_ANALYSIS_SYSTEM_PROMPT = """
Você é um analista financeiro especialista do Stonks AI, com foco em análise de ações
da B3 (Brasil) e NYSE/Nasdaq (EUA). Suas análises devem ser:

1. Técnicas: Baseadas em dados reais de preço, volume e indicadores
2. Fundamentalistas: Considere P/L, P/VP, DY, ROE, margens, dívida
3. Contextuais: Leve em conta setor, cenário macroeconômico e notícias relevantes
4. Objetivas: Apresente riscos e oportunidades de forma equilibrada
5. Didáticas: Explique termos técnicos de forma acessível

Formato de resposta:
- Resumo Executivo (2-3 linhas)
- Análise Técnica (preço, tendência, suportes/resistências)
- Análise Fundamentalista (múltiplos, rentabilidade, saúde financeira)
- Riscos
- Oportunidades
- Recomendação Geral (Compra/Mantém/Vende com justificativa)

Como ler os indicadores:
- Cite explicitamente o P/L e o P/VP fornecidos. P/L negativo significa que a empresa teve prejuízo.
- Beta acima de 1 indica que a ação oscila mais que o mercado.
- Use os números exatamente como fornecidos; não invente valores que não estão nos dados.
- Termine lembrando que a análise não é recomendação de investimento.

Use português brasileiro claro e objetivo.
"""

FINANCIAL_COMPARISON_PROMPT = """
Compare as seguintes ações lado a lado:

{ações}

Para cada ação, analise:
1. Performance recente (variação % no período)
2. Múltiplos de mercado (P/L, P/VP, DY)
3. Saúde financeira (dívida, margens, ROE)
4. Perspectivas do setor

Conclua com uma recomendação comparativa ranqueada da melhor para pior opção
de investimento no momento, considerando a relação risco-retorno.
"""

# Curto de propósito: com o prompt longo antigo, o qwen2.5:3b deixava de usar as ferramentas
# em perguntas sobre o dinheiro do usuário (78% contra 94% de acerto em evals/tools_eval.py)
FINANCIAL_CHAT_SYSTEM_PROMPT = """
Você é o assistente do Stonks AI, um app de finanças pessoais e investimentos. Responda em
português do Brasil, de forma clara, direta e didática.
- Não preveja preços nem diga se um ativo vai subir ou cair: explique que não dá para prever.
- Se a pergunta for sobre comprar ou vender um ativo específico, diga que isto não é
  recomendação de investimento.
- Retorno alto garantido, ou ganho por convidar outras pessoas, é sinal de golpe ou pirâmide
  financeira: diga isso claramente.
- Se não souber, admita em vez de inventar.
"""

# Entra no prompt do chat quando a base de conhecimento tem verbetes relevantes
CHAT_REFERENCE_BLOCK = """

REFERÊNCIAS CONFERIDAS (use como fonte principal; não contradiga estes fatos e
repita os números exatamente como estão):

{context}
"""

# ── Prompts de Finanças Pessoais ────────────────────────────────────────

FINANCIAL_MONTHLY_SUMMARY_PROMPT = """
Analise o resumo financeiro mensal abaixo e gere um texto curto e útil em português brasileiro.

MÊS: {month}/{year}
RECEITAS: R$ {total_income:.2f}
DESPESAS: R$ {total_expense:.2f}
SALDO: R$ {balance:.2f}
MÉDIA DIÁRIA: R$ {avg_daily_expense:.2f}
TRANSAÇÕES: {transaction_count}

GASTOS POR CATEGORIA:
{categories}

FATOS JÁ CALCULADOS (use exatamente, sem refazer contas):
- Saldo do mês: {balance_fact}
- Principal categoria de gasto: {top_category_fact}

Escreva um parágrafo curto destacando:
1. O saldo do mês (positivo ou negativo), como nos fatos acima
2. A principal categoria de gasto, como nos fatos acima
3. Uma dica prática baseada nos dados
4. Tom neutro e informativo (sem alarmismo)
"""

FINANCIAL_GOAL_ANALYSIS_PROMPT = """
Você é um consultor financeiro pessoal. Analise a meta abaixo e gere
um plano de ação personalizado em português brasileiro.

META: {goal_name}
VALOR ALVO: R$ {target:.2f}
VALOR ATUAL: R$ {current:.2f}
FALTA: R$ {remaining:.2f}
PROGRESSO: {progress}%
PRAZO: {deadline}
DIAS RESTANTES: {days_left}
ECONOMIA MENSAL NECESSÁRIA: R$ {monthly_needed:.2f}

DADOS DO USUÁRIO:
- Gasto médio diário: R$ {avg_daily_expense:.2f}
- Renda mensal: R$ {monthly_income:.2f}
- Sobra mensal estimada (renda menos 30 dias de gasto médio): R$ {free_income:.2f}

VEREDITO JÁ CALCULADO (use exatamente, sem refazer contas): {verdict}

Sua resposta deve incluir:
1. ✅ Viabilidade da meta, conforme o veredito acima
2. 📊 Plano de ação com economia mensal sugerida
3. 💡 Dicas práticas para acelerar o progresso
4. ⚠️ Alertas sobre possíveis obstáculos

Seja prático e motivacional, mas realista. Ao citar valores, use apenas os números acima.
"""


def _brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def build_chat_system_prompt(question: str) -> str:
    """Prompt do chat com os verbetes da base de conhecimento relevantes para a pergunta."""
    from stonks_ai.knowledge import context_for

    context = context_for(question)
    if not context:
        return FINANCIAL_CHAT_SYSTEM_PROMPT
    return FINANCIAL_CHAT_SYSTEM_PROMPT + CHAT_REFERENCE_BLOCK.format(context=context)


def chat_query_from_messages(messages: list) -> str:
    """Texto usado na busca: a última pergunta e a anterior (para perguntas de continuação)."""
    user_msgs = [m["content"] for m in messages if m.get("role") == "user"]
    return " ".join(user_msgs[-2:])


def format_monthly_summary_prompt(month: int, year: int, summary: dict) -> str:
    """Prompt do resumo mensal. Os fatos que o modelo costuma errar vêm prontos do Python."""
    cats = summary.get("top_categories") or []
    categories = "\n".join(f"  - {c['name']}: R$ {c['amount']:.2f} ({c['percent']}%)" for c in cats)
    balance = summary["balance"]
    if balance >= 0:
        balance_fact = f"POSITIVO: sobraram {_brl(balance)}"
    else:
        balance_fact = f"NEGATIVO: as despesas superaram as receitas em {_brl(-balance)}"
    if cats:
        top = max(cats, key=lambda c: c["amount"])
        top_fact = f"{top['name']}, com {_brl(top['amount'])} ({top['percent']}% das despesas)"
    else:
        top_fact = "não há despesas categorizadas"
    return FINANCIAL_MONTHLY_SUMMARY_PROMPT.format(
        month=month, year=year,
        total_income=summary["total_income"], total_expense=summary["total_expense"],
        balance=balance, avg_daily_expense=summary["avg_daily_expense"],
        transaction_count=summary["transaction_count"], categories=categories,
        balance_fact=balance_fact, top_category_fact=top_fact,
    )


def goal_verdict(remaining: float, monthly_needed: float, free_income: float) -> str:
    """Viabilidade da meta calculada em Python (modelos pequenos erram essa conta)."""
    if remaining <= 0:
        return "META JÁ ALCANÇADA."
    if free_income <= 0:
        return ("INVIÁVEL: os gastos médios já consomem toda a renda; "
                "é preciso reduzir gastos antes de guardar para a meta.")
    share = monthly_needed / free_income
    if share <= 0.5:
        return f"VIÁVEL: exige guardar {share:.0%} do que sobra por mês ({_brl(monthly_needed)})."
    if share <= 1:
        return f"APERTADA: exige guardar {share:.0%} do que sobra por mês ({_brl(monthly_needed)})."
    months = -(-remaining // (free_income * 0.5))  # arredonda para cima
    return (f"INVIÁVEL NO PRAZO ATUAL: seria preciso guardar {_brl(monthly_needed)} por mês, "
            f"mas sobram cerca de {_brl(free_income)}. Guardando metade da sobra, "
            f"a meta levaria cerca de {months:.0f} meses: sugira aumentar o prazo ou reduzir o valor.")


def format_goal_prompt(
    goal_name: str, target: float, current: float, remaining: float, progress: float,
    deadline: str, days_left, monthly_needed: float, avg_daily_expense: float,
    monthly_income: float,
) -> str:
    """Prompt da análise de meta, com a sobra mensal e o veredito já calculados."""
    free_income = monthly_income - avg_daily_expense * 30
    return FINANCIAL_GOAL_ANALYSIS_PROMPT.format(
        goal_name=goal_name, target=target, current=current, remaining=remaining,
        progress=progress, deadline=deadline, days_left=days_left,
        monthly_needed=monthly_needed, avg_daily_expense=avg_daily_expense,
        monthly_income=monthly_income, free_income=free_income,
        verdict=goal_verdict(remaining, monthly_needed, free_income),
    )


def _as_percent(fraction) -> str:
    """0.061 -> '6.1%'. Deixa explícita a unidade para o modelo não confundir fração com percentual."""
    if fraction is None:
        return "N/A"
    try:
        return f"{float(fraction) * 100:.1f}%"
    except (TypeError, ValueError):
        return str(fraction)


def format_stock_analysis_prompt(quote_data: dict, fundamentals: dict = None) -> str:
    """Formata o prompt de análise de ações com dados reais."""
    prompt = f"""
ATIVO: {quote_data.get('ticker')} ({quote_data.get('name', '')})
BOLSA: {quote_data.get('exchange')}
DATA: {quote_data.get('timestamp')}

DADOS DE MERCADO:
- Preço: {quote_data.get('currency')} {quote_data.get('price'):.2f}
- Variação: {quote_data.get('change_percent'):.2f}%
- Máxima dia: {quote_data.get('high'):.2f}
- Mínima dia: {quote_data.get('low'):.2f}
- Abertura: {quote_data.get('open_price'):.2f}
- Fechamento anterior: {quote_data.get('previous_close'):.2f}
- Volume: {quote_data.get('volume'):,}
"""

    if fundamentals:
        prompt += f"""
DADOS FUNDAMENTALISTAS:
- Setor: {fundamentals.get('sector', 'N/A')}
- Market Cap: {fundamentals.get('currency')} {fundamentals.get('market_cap', 0):,.0f}
- P/L: {fundamentals.get('pe_ratio', 'N/A')}
- P/VP: {fundamentals.get('pb_ratio', 'N/A')}
- Dividend Yield (12 meses): {_as_percent(fundamentals.get('dividend_yield'))}
- ROE: {_as_percent(fundamentals.get('roe'))}
- Margem Líquida: {_as_percent(fundamentals.get('net_margin'))}
- Beta: {fundamentals.get('beta', 'N/A')}
"""

    prompt += "\nFaça uma análise completa deste ativo seguindo o formato padrão."
    return prompt
