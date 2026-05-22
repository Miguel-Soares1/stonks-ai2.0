"""
Stonks AI - Assistente financeiro com IA via CLI.

Entry point da aplicação. Comandos disponíveis:
    stonks quote TICKER        - Cotação atual
    stonks history TICKER      - Histórico de preços
    stonks analyze TICKER      - Análise completa com IA
    stonks compare TICKERS...  - Comparar múltiplas ações
    stonks watchlist           - Gerenciar watchlist
    stonks chat PERGUNTA       - Chat financeiro com IA
    stonks finance COMANDO     - Finanças pessoais (dashboard, importar, transações)
    stonks goals COMANDO       - Metas financeiras
    stonks alerts COMANDO      - Alertas inteligentes
    stonks config              - Configurações
    stonks init                - Inicializar banco/config
"""

import os
import sys
from typing import List, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text

from stonks_ai import __version__
from stonks_ai.agents.financial_agent import FinancialAgent
from stonks_ai.agents.personal_finance_agent import PersonalFinanceAgent
from stonks_ai.collectors.stocks.base import StockCollectorError
from stonks_ai.config import ConfigError, config
from stonks_ai.database import DatabaseError, db
from stonks_ai.llm.client import LLMError
from stonks_ai.models.watchlist import WatchlistItem
from stonks_ai.utils.charts import render_line_chart
from stonks_ai.utils.formatters import (
    format_change,
    format_currency,
    format_large_number,
    format_percent,
    format_ticker_display,
)
from stonks_ai.utils.validators import detect_exchange

# Força UTF-8 no terminal Windows para compatibilidade com emojis
if sys.platform == "win32" and not os.environ.get("PYTEST_VERSION"):
    try:
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
        # Reconfigura stdout/stderr para UTF-8 (Python 3.7+)
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Configura o Console do Rich para evitar legacy renderer no Windows
console = Console(legacy_windows=False)

# Agentes globais
financial_agent = FinancialAgent()
personal_finance_agent = PersonalFinanceAgent()


def print_banner():
    """Exibe banner de inicialização."""
    banner = """
╔══════════════════════════════════════════╗
║        🚀  S T O N K S  A I             ║
║    Assistente Financeiro Inteligente      ║
║         B3 · NYSE · Vagas · IA           ║
╚══════════════════════════════════════════╝
    """
    console.print(Panel(banner, style="bold cyan"), justify="center")


# ====== COMMAND: quote ======
@click.command()
@click.argument("ticker")
@click.option("--exchange", "-e", default=None, help="Bolsa: B3 ou NYSE")
def quote(ticker: str, exchange: Optional[str]):
    """Obtém cotação atual de uma ação."""
    try:
        if exchange is None:
            exchange = detect_exchange(ticker)

        q = financial_agent.get_quote(ticker, exchange)

        table = Table(show_header=False, box=box.ROUNDED, title=f"[bold]{format_ticker_display(q.ticker, q.exchange)}[/]")
        table.add_column("Indicador", style="cyan")
        table.add_column("Valor", style="white")

        table.add_row("Empresa", q.name)
        table.add_row("Preço", format_currency(q.price, q.currency))
        table.add_row("Variação", format_change(q.change, q.change_percent))
        table.add_row("Máxima", format_currency(q.high, q.currency))
        table.add_row("Mínima", format_currency(q.low, q.currency))
        table.add_row("Abertura", format_currency(q.open_price, q.currency))
        table.add_row("Fech. Ant.", format_currency(q.previous_close, q.currency))
        table.add_row("Volume", format_large_number(q.volume))

        console.print(table)

    except StockCollectorError as e:
        console.print(f"[red]❌ {e}[/]")
    except Exception as e:
        console.print(f"[red]Erro inesperado: {e}[/]")


# ====== COMMAND: history ======
@click.command()
@click.argument("ticker")
@click.option("--exchange", "-e", default=None, help="Bolsa: B3 ou NYSE")
@click.option("--period", "-p", default="1mo", help="Período: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max")
@click.option("--chart/--no-chart", default=True, help="Mostrar gráfico")
def history(ticker: str, exchange: Optional[str], period: str, chart: bool):
    """Obtém histórico de preços de uma ação."""
    try:
        if exchange is None:
            exchange = detect_exchange(ticker)

        h = financial_agent.get_history(ticker, exchange, period=period)

        if not h.data:
            console.print(f"[yellow]⚠️ Nenhum dado histórico para {ticker} no período {period}.[/]")
            return

        # Mostra tabela resumo
        first = h.data[0]
        last = h.data[-1]

        change = last["close"] - first["close"]
        change_pct = (change / first["close"] * 100) if first["close"] else 0

        console.print(f"[bold cyan]📊 {ticker} - {period}[/]")
        console.print(f"   Período: {first['date'][:10]} até {last['date'][:10]}")
        console.print(f"   Variação: {format_change(change, change_pct)}")
        console.print(f"   Média: {sum(d['close'] for d in h.data) / len(h.data):.2f}")

        # Gráfico
        if chart:
            try:
                chart_str = render_line_chart(
                    h.data,
                    title=f"{ticker} - {period}",
                )
                console.print(chart_str)
            except Exception as e:
                console.print(f"[yellow]⚠️ Erro ao gerar gráfico: {e}[/]")

        # Tabela compacta dos últimos dias
        table = Table(box=box.SIMPLE, title="Últimos pregões")
        table.add_column("Data", style="cyan")
        table.add_column("Abertura", justify="right")
        table.add_column("Máxima", justify="right")
        table.add_column("Mínima", justify="right")
        table.add_column("Fechamento", justify="right")
        table.add_column("Volume", justify="right")

        for entry in h.data[-15:]:  # Últimos 15 dias
            table.add_row(
                entry["date"][:10],
                f"{entry['open']:.2f}",
                f"{entry['high']:.2f}",
                f"{entry['low']:.2f}",
                f"{entry['close']:.2f}",
                format_large_number(entry["volume"]),
            )

        console.print(table)

    except StockCollectorError as e:
        console.print(f"[red]❌ {e}[/]")
    except Exception as e:
        console.print(f"[red]Erro inesperado: {e}[/]")


# ====== COMMAND: analyze ======
@click.command()
@click.argument("ticker")
@click.option("--exchange", "-e", default=None, help="Bolsa: B3 ou NYSE")
def analyze(ticker: str, exchange: Optional[str]):
    """Análise completa de uma ação com IA."""
    try:
        with console.status(f"[bold green]Analisando {ticker}...[/]"):
            if exchange is None:
                exchange = detect_exchange(ticker)

            result = financial_agent.analyze(ticker, exchange)

        # Mostra cotação
        q = result["quote"]
        table = Table(show_header=False, box=box.ROUNDED, title=f"[bold]{format_ticker_display(q.ticker, q.exchange)}[/]")
        table.add_column("Indicador", style="cyan")
        table.add_column("Valor", style="white")
        table.add_row("Empresa", q.name)
        table.add_row("Preço", format_currency(q.price, q.currency))
        table.add_row("Variação", format_change(q.change, q.change_percent))
        console.print(table)

        # Mostra fundamentos
        fund = result.get("fundamentals")
        if fund:
            ftable = Table(show_header=False, box=box.SIMPLE, title="📊 Fundamentos")
            ftable.add_column("Indicador", style="cyan")
            ftable.add_column("Valor", style="white")

            ftable.add_row("Setor", fund.sector)
            ftable.add_row("Market Cap", format_large_number(fund.market_cap))
            if fund.pe_ratio:
                ftable.add_row("P/L", f"{fund.pe_ratio:.2f}")
            if fund.dividend_yield:
                ftable.add_row("Dividend Yield", format_percent(fund.dividend_yield))
            if fund.roe:
                ftable.add_row("ROE", format_percent(fund.roe))
            if fund.beta:
                ftable.add_row("Beta", f"{fund.beta:.2f}")
            if fund.pb_ratio:
                ftable.add_row("P/VP", f"{fund.pb_ratio:.2f}")

            console.print(ftable)

        # Análise IA
        analysis = result.get("analysis", "")
        if analysis and "não disponível" not in analysis.lower():
            console.print(Panel(
                analysis,
                title="🤖 Análise IA",
                border_style="green",
                width=80,
            ))
        elif analysis:
            console.print(f"[yellow]⚠️ {analysis}[/]")

    except StockCollectorError as e:
        console.print(f"[red]❌ {e}[/]")
    except Exception as e:
        console.print(f"[red]Erro inesperado: {e}[/]")


# ====== COMMAND: compare ======
@click.command()
@click.argument("tickers", nargs=-1, required=True)
def compare(tickers: List[str]):
    """Compara duas ou mais ações."""
    if len(tickers) < 2:
        console.print("[red]❌ Informe pelo menos 2 tickers para comparar.[/]")
        return

    try:
        with console.status(f"[bold green]Comparando {', '.join(tickers)}...[/]"):
            result = financial_agent.compare(list(tickers))

        # Tabela comparativa
        table = Table(box=box.ROUNDED, title="📊 Comparação")
        table.add_column("Ticker", style="cyan", width=12)
        table.add_column("Preço", justify="right", width=12)
        table.add_column("Variação", justify="right", width=12)
        table.add_column("P/L", justify="right", width=10)
        table.add_column("DY", justify="right", width=10)

        for q, f in zip(result["quotes"], result["fundamentals"]):
            table.add_row(
                q.ticker,
                format_currency(q.price, q.currency),
                f"{q.change_percent:+.2f}%",
                f"{f.pe_ratio:.2f}" if f and f.pe_ratio else "N/A",
                format_percent(f.dividend_yield) if f and f.dividend_yield else "N/A",
            )

        console.print(table)

        # Análise IA
        analysis = result.get("analysis", "")
        if analysis and "não disponível" not in analysis.lower():
            console.print(Panel(analysis, title="🤖 Análise Comparativa IA", border_style="green"))

    except Exception as e:
        console.print(f"[red]❌ Erro: {e}[/]")


# ====== COMMAND: watchlist ======
@click.command()
@click.option("--add", "-a", help="Adicionar ticker à watchlist")
@click.option("--remove", "-r", help="Remover ticker da watchlist")
@click.option("--exchange", "-e", default="B3", help="Bolsa do ticker")
@click.option("--name", "-n", default="Minha Watchlist", help="Nome da watchlist")
def watchlist(add: Optional[str], remove: Optional[str], exchange: str, name: str):
    """Gerencia a watchlist de ações."""
    try:
        with db.session() as session:
            if add:
                item = WatchlistItem(
                    name=name,
                    ticker=add.upper(),
                    exchange=exchange.upper(),
                )
                session.add(item)
                console.print(f"[green]✅ {add.upper()} adicionado à watchlist![/]")
                return

            if remove:
                items = session.query(WatchlistItem).filter(
                    WatchlistItem.ticker == remove.upper()
                ).all()
                for item in items:
                    session.delete(item)
                console.print(f"[green]✅ {remove.upper()} removido da watchlist![/]")
                return

            # Lista watchlist
            items = session.query(WatchlistItem).all()

            if not items:
                console.print("[yellow]📋 Watchlist vazia. Use --add para adicionar tickers.[/]")
                return

            # Busca cotações atuais
            table = Table(box=box.ROUNDED, title="📋 Watchlist")
            table.add_column("Ticker", style="cyan")
            table.add_column("Bolsa", style="blue")
            table.add_column("Preço", justify="right")
            table.add_column("Variação", justify="right")
            table.add_column("Alvo", justify="right")

            for item in items:
                try:
                    q = financial_agent.get_quote(item.ticker, item.exchange)
                    target_str = format_currency(item.target_price, q.currency) if item.target_price else "-"
                    table.add_row(
                        q.ticker,
                        item.exchange,
                        format_currency(q.price, q.currency),
                        f"{q.change_percent:+.2f}%",
                        target_str,
                    )
                except StockCollectorError:
                    table.add_row(
                        item.ticker,
                        item.exchange,
                        "[red]Erro[/]",
                        "-",
                        "-",
                    )

            console.print(table)

    except DatabaseError as e:
        console.print(f"[red]❌ Erro no banco: {e}[/]")
    except Exception as e:
        console.print(f"[red]❌ Erro: {e}[/]")


# ====== COMMAND: chat ======
@click.command()
@click.argument("question", nargs=-1, required=False)
@click.option(
    "--interactive", "-i", is_flag=True,
    help="Modo interativo (conversa contínua)",
)
def chat(question: tuple, interactive: bool):
    """💬 Chat financeiro — Tire dúvidas sobre investimentos e finanças.

    Faça perguntas sobre mercado financeiro, indicadores, estratégias
    de investimento, economia e muito mais.

    Exemplos:

        stonks chat "O que é P/L?"

        stonks chat "Qual a diferença entre CDB e Tesouro Direto?"

        stonks chat -i  (modo interativo)
    """
    try:
        if interactive:
            # Modo interativo
            console.print("[bold cyan]💬 Chat Financeiro Stonks AI[/]")
            console.print(
                "[yellow]Digite sua dúvida ou 'sair' para encerrar.[/]\n"
            )

            conversation_history = []
            while True:
                try:
                    question_text = click.prompt(
                        Text("Você", style="cyan"),
                        prompt_suffix=" > ",
                    )
                except click.Abort:
                    console.print("\n[yellow]Chat encerrado.[/]")
                    break

                if question_text.lower() in ("sair", "quit", "exit", "q"):
                    console.print("[yellow]Chat encerrado. Até mais! 👋[/]")
                    break

                if not question_text.strip():
                    continue

                with console.status("[bold green]🤔 Pensando...[/]"):
                    try:
                        response = financial_agent.chat(
                            message=question_text,
                            conversation_history=conversation_history,
                        )
                    except Exception as e:
                        console.print(f"[red]❌ Erro: {e}[/]")
                        continue

                # Atualiza histórico
                conversation_history.append(
                    {"role": "user", "content": question_text}
                )
                conversation_history.append(
                    {"role": "assistant", "content": response}
                )

                # Limita histórico para não estourar contexto
                if len(conversation_history) > 20:
                    conversation_history = conversation_history[-20:]

                console.print(Panel(
                    response,
                    title="🤖 Stonks AI",
                    border_style="green",
                    width=100,
                ))
                console.print()
        else:
            # Modo pergunta única
            if not question:
                console.print("[yellow]❓ Digite sua pergunta ou use --interactive para modo conversa.[/]")
                console.print("Exemplos:")
                console.print("  stonks chat \"O que é P/L?\"")
                console.print("  stonks chat -i")
                return

            question_text = " ".join(question)

            with console.status("[bold green]🤔 Pensando...[/]"):
                response = financial_agent.chat(message=question_text)

            console.print(Panel(
                response,
                title="🤖 Stonks AI",
                border_style="green",
                width=100,
            ))

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Operação cancelada pelo usuário.[/]")
    except Exception as e:
        console.print(f"[red]❌ Erro: {e}[/]")


# ====== COMMAND: init ======
@click.command()
def init():
    """Inicializa banco de dados e configuração."""
    try:
        # Config
        console.print("[cyan]📁 Verificando configuração...[/]")
        _ = config.data  # Força carregamento/criação
        console.print(f"[green]✅ Config: {config.config_path}[/]")

        # Banco
        console.print("[cyan]🗄️  Inicializando banco de dados...[/]")
        db.initialize()
        console.print(f"[green]✅ Banco: {db.db_path}[/]")

        # Finanças pessoais
        console.print("[cyan]💰 Inicializando módulo de finanças pessoais...[/]")
        fin_result = personal_finance_agent.initialize()
        if fin_result["categories"] > 0:
            console.print(f"[green]✅ {fin_result['categories']} categorias padrão criadas[/]")
        if fin_result["alert_configs"] > 0:
            console.print(f"[green]✅ {fin_result['alert_configs']} configurações de alerta criadas[/]")
        console.print()

        # Ready
        print_banner()
        console.print("[bold green]✅ Stonks AI pronto para uso![/]")
        console.print("\nComandos disponíveis:")
        console.print("  stonks quote PETR4         → Cotação B3")
        console.print("  stonks quote AAPL -e NYSE  → Cotação NYSE")
        console.print("  stonks analyze PETR4       → Análise com IA")
        console.print("  stonks compare PETR4 VALE3 → Comparar")
        console.print("  stonks history PETR4 -p 1y → Histórico")
        console.print("  stonks watchlist --add PETR4 → Watchlist")
        console.print("  stonks chat 'O que é P/L?'   → Chat financeiro")
        console.print("  stonks chat -i               → Chat interativo")

    except (ConfigError, DatabaseError) as e:
        console.print(f"[red]❌ Erro de inicialização: {e}[/]")
    except Exception as e:
        console.print(f"[red]❌ Erro inesperado: {e}[/]")


# ====== COMMAND: config (show/set) ======
@click.command()
@click.option("--show", is_flag=True, help="Mostrar configuração atual")
@click.option("--set", "set_key", nargs=2, metavar="KEY VALUE", help="Definir config (ex: llm.model llama3.2:3b)")
def config_cmd(show: bool, set_key: Optional[tuple]):
    """Gerencia configurações do Stonks AI."""
    if set_key:
        key, value = set_key
        try:
            # Suporta chaves aninhadas: llm.model
            keys = key.split(".")
            if len(keys) == 2:
                config.set(value, keys[0], keys[1])
            else:
                config.set(value, keys[0])
            console.print(f"[green]✅ Config atualizada: {key} = {value}[/]")
        except Exception as e:
            console.print(f"[red]❌ Erro: {e}[/]")
        return

    if show:
        import yaml
        console.print("[bold cyan]⚙️ Configuração Atual:[/]")
        console.print(yaml.dump(config.data, default_flow_style=False))
        return

    console.print("[yellow]Use --show para ver config ou --set KEY VALUE para alterar.[/]")


# ====== COMMAND: version ======
@click.command()
def version():
    """Mostra versão do Stonks AI."""
    console.print(f"[bold cyan]Stonks AI v{__version__}[/]")
    console.print("Assistente financeiro com IA local")
    console.print("B3 · NYSE · Finanças Pessoais")


# ====== COMMAND: finance ======
@click.group()
def finance():
    """💰 Finanças pessoais — Dashboard, transações e importação de extratos."""
    pass


@finance.command()
@click.option("--year", "-y", type=int, default=None, help="Ano (ex: 2025)")
@click.option("--month", "-m", type=int, default=None, help="Mês (1-12)")
@click.option("--ai", is_flag=True, help="Incluir resumo com IA")
@click.pass_context
def dashboard(ctx, year, month, ai):
    """Dashboard financeiro completo com resumo do mês."""
    try:
        with console.status("[bold green]Montando dashboard financeiro..."):
            data = personal_finance_agent.get_dashboard(year, month)
            summary = data["summary"]

            now = __import__("datetime").datetime.now()
            year = year or now.year
            month = month or now.month

            # Header
            console.print(f"\n[bold cyan]📊 Dashboard Financeiro — {month:02d}/{year}[/]\n")

            # Summary table
            table = Table(show_header=False, box=box.ROUNDED, title="Resumo do Mês")
            table.add_column("Indicador", style="cyan")
            table.add_column("Valor", style="white")

            table.add_row("💰 Receitas", format_currency(summary["total_income"], "BRL"))
            table.add_row("💸 Despesas", format_currency(summary["total_expense"], "BRL"))
            table.add_row("📊 Saldo", format_currency(summary["balance"], "BRL"))
            table.add_row("📈 Média Diária", format_currency(summary["avg_daily_expense"], "BRL"))
            table.add_row("🔄 Transações", str(summary["transaction_count"]))
            console.print(table)
            console.print()

            # Top categories
            if summary["top_categories"]:
                cat_table = Table(box=box.ROUNDED, title="Categorias com Mais Gastos")
                cat_table.add_column("Categoria", style="cyan")
                cat_table.add_column("Valor", style="white", justify="right")
                cat_table.add_column("%", style="yellow", justify="right")
                for cat in summary["top_categories"]:
                    cat_table.add_row(
                        cat["name"],
                        format_currency(cat["amount"], "BRL"),
                        f"{cat['percent']:.1f}%",
                    )
                console.print(cat_table)
                console.print()

            # Active goals
            if data["active_goals"]:
                goal_table = Table(box=box.ROUNDED, title="Metas Ativas")
                goal_table.add_column("Meta", style="cyan")
                goal_table.add_column("Progresso", style="white", justify="right")
                goal_table.add_column("Status", style="yellow")
                for g in data["active_goals"]:
                    goal_table.add_row(
                        g["name"],
                        f"R$ {g['current_amount']:,.2f} / R$ {g['target_amount']:,.2f}",
                        "No prazo" if g.get("is_on_track") else "Atenção",
                    )
                console.print(goal_table)
                console.print()

            # Active alerts
            if data["active_alerts"]:
                console.print("[bold yellow]Alertas Ativos:[/]")
                for a in data["active_alerts"][:5]:
                    icon = "🔴" if a["severity"] == "high" else "🟡" if a["severity"] == "medium" else "🟢"
                    console.print(f"  {icon} [{a['alert_type']}] {a['title']}")
                console.print()

            # AI Summary
            if ai:
                with console.status("[bold green]Gerando resumo com IA..."):
                    ai_text = personal_finance_agent.get_monthly_summary_ai(year, month)
                    if ai_text:
                        console.print(Panel(ai_text, title="Análise com IA", border_style="green"))
                        console.print()

    except Exception as e:
        console.print(f"[red]Erro ao gerar dashboard: {e}[/]")


@finance.command(name="import")
@click.argument("file_path")
def import_file(file_path):
    """Importar extrato bancario (CSV/Excel/PDF)."""
    try:
        with console.status(f"[bold green]Importando {file_path}..."):
            result = personal_finance_agent.import_file(file_path)

        if result["errors"]:
            for err in result["errors"]:
                console.print(f"[red]{err}[/]")
        if result["duplicates"] > 0:
            console.print(f"[yellow]{result['duplicates']} duplicatas ignoradas[/]")
        if result["imported"] > 0:
            console.print(f"[green]{result['imported']} transacoes importadas com sucesso![/]")
        else:
            console.print("[red]Nenhuma transacao importada.[/]")

    except Exception as e:
        console.print(f"[red]Erro ao importar arquivo: {e}[/]")


@finance.command()
@click.option("--limit", "-l", type=int, default=50, help="Maximo de transacoes")
@click.option("--type", "-t", "tx_type", type=click.Choice(["expense", "income"]), default=None, help="Filtrar por tipo")
@click.option("--days", "-d", type=int, default=None, help="Filtrar por dias recentes")
@click.option("--category", "-c", "category_id", type=int, default=None, help="Filtrar por ID da categoria")
def transactions(limit, tx_type, days, category_id):
    """Lista transacoes financeiras."""
    try:
        with console.status("[bold green]Buscando transacoes..."):
            tx_list = personal_finance_agent.list_transactions(
                limit=limit,
                transaction_type=tx_type,
                days=days,
                category_id=category_id,
            )

        if not tx_list:
            console.print("[yellow]Nenhuma transacao encontrada.[/]")
            return

        table = Table(box=box.ROUNDED, title="Transacoes")
        table.add_column("ID", style="dim", justify="right")
        table.add_column("Data", style="cyan")
        table.add_column("Descricao", style="white")
        table.add_column("Categoria", style="yellow")
        table.add_column("Valor", style="white", justify="right")

        for tx in tx_list:
            prefix = "[green]+" if tx["type"] == "income" else "[red]-"
            date_str = tx["date"].strftime("%d/%m/%Y") if hasattr(tx["date"], "strftime") else str(tx["date"])[:10]
            table.add_row(
                str(tx["id"]),
                date_str,
                tx["description"][:50],
                tx.get("category_name") or "-",
                f"{prefix} R$ {tx['amount']:,.2f}[/]",
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Erro ao listar transacoes: {e}[/]")


@finance.command()
@click.argument("description")
@click.argument("amount", type=float)
@click.option("--date", default=None, help="Data (YYYY-MM-DD)")
@click.option("--type", "-t", "tx_type", default="expense", help="Tipo: expense ou income")
@click.option("--category", "-c", "category_name", default=None, help="Nome da categoria")
@click.option("--notes", "-n", default=None, help="Observacoes")
def add(description, amount, tx_type, date, category_name, notes):
    """Adiciona transacao manualmente."""
    try:
        with console.status("[bold green]Adicionando transacao..."):
            tx = personal_finance_agent.add_transaction(
                description=description,
                amount=amount,
                date=date,
                tx_type=tx_type,
                category_name=category_name,
                notes=notes,
            )
        console.print(f"[green]Transacao adicionada: {tx['description']} - R$ {tx['amount']:,.2f}[/]")
        if tx.get("category_name"):
            console.print(f"   Categoria: {tx['category_name']}")

    except Exception as e:
        console.print(f"[red]Erro ao adicionar transacao: {e}[/]")


@finance.command()
@click.argument("transaction_id", type=int)
@click.argument("new_category")
def recategorize(transaction_id, new_category):
    """Reclassifica uma transacao."""
    try:
        with console.status("[bold green]Reclassificando..."):
            success = personal_finance_agent.update_transaction_category(
                transaction_id, new_category
            )
        if success:
            console.print(f"[green]Transacao {transaction_id} reclassificada como '{new_category}'[/]")
        else:
            console.print(f"[red]Nao foi possivel reclassificar a transacao {transaction_id}[/]")

    except Exception as e:
        console.print(f"[red]Erro: {e}[/]")


@finance.command()
@click.argument("transaction_id", type=int)
def delete(transaction_id):
    """Remove uma transacao."""
    try:
        success = personal_finance_agent.delete_transaction(transaction_id)
        if success:
            console.print(f"[green]Transacao {transaction_id} removida.[/]")
        else:
            console.print(f"[red]Transacao {transaction_id} nao encontrada.[/]")

    except Exception as e:
        console.print(f"[red]Erro: {e}[/]")


@finance.command()
def categories():
    """Lista categorias disponiveis."""
    try:
        with console.status("[bold green]Buscando categorias..."):
            cats = personal_finance_agent.list_categories()

        if not cats:
            console.print("[yellow]Nenhuma categoria encontrada.[/]")
            return

        table = Table(box=box.ROUNDED, title="Categorias")
        table.add_column("ID", style="dim", justify="right")
        table.add_column("Icone", style="white")
        table.add_column("Nome", style="cyan")
        table.add_column("Limite", style="white", justify="right")

        for c in cats:
            limit_str = (
                format_currency(c["budget_limit"] / 100, "BRL")
                if c.get("budget_limit")
                else "-"
            )
            table.add_row(
                str(c["id"]),
                c.get("icon", "📦"),
                c["name"],
                limit_str,
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Erro ao listar categorias: {e}[/]")


# ====== COMMAND: goals ======
@click.group()
def goals():
    """🎯 Metas financeiras."""
    pass


@goals.command()
@click.argument("name")
@click.argument("target_amount", type=float)
@click.option("--deadline", default=None, help="Prazo (YYYY-MM-DD)")
@click.option("--type", "-t", "goal_type", default="savings", help="Tipo: savings, debt, investment, custom")
@click.option("--priority", "-p", default="medium", help="Prioridade: low, medium, high")
@click.option("--description", "-d", default=None, help="Descricao")
def create(name, target_amount, deadline, goal_type, priority, description):
    """Cria uma nova meta financeira."""
    try:
        with console.status("[bold green]Criando meta..."):
            goal = personal_finance_agent.create_goal(
                name=name,
                target_amount=target_amount,
                deadline=deadline,
                goal_type=goal_type,
                priority=priority,
                description=description,
            )
        console.print(f"[green]Meta criada: {goal['name']}[/]")
        console.print(f"   Valor alvo: R$ {goal['target_amount']:,.2f}")
        if goal.get("deadline"):
            d = goal["deadline"]
            d_str = d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else str(d)[:10]
            console.print(f"   Prazo: {d_str}")

    except Exception as e:
        console.print(f"[red]Erro ao criar meta: {e}[/]")


@goals.command(name="list")
@click.option("--status", "-s", default="active", help="Filtrar: active, completed, all")
def list_goals(status):
    """Lista metas financeiras."""
    try:
        status_filter = None if status == "all" else status
        with console.status("[bold green]Buscando metas..."):
            goal_list = personal_finance_agent.list_goals(status=status_filter)

        if not goal_list:
            console.print("[yellow]Nenhuma meta encontrada.[/]")
            return

        table = Table(box=box.ROUNDED, title="Metas Financeiras")
        table.add_column("ID", style="dim", justify="right")
        table.add_column("Meta", style="cyan")
        table.add_column("Progresso", style="white", justify="right")
        table.add_column("%", style="yellow", justify="right")
        table.add_column("Status", style="white")
        table.add_column("Prazo", style="white")

        for g in goal_list:
            pct = g.get("progress_percent", 0)
            pct_str = f"{pct:.1f}%" if pct else "-"
            status_display = {
                "active": "Ativa",
                "completed": "Completa",
                "paused": "Pausada",
                "cancelled": "Cancelada",
            }.get(g["status"], g["status"])

            d_str = "-"
            if g.get("deadline"):
                d = g["deadline"]
                d_str = d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else str(d)[:10]

            table.add_row(
                str(g["id"]),
                g["name"],
                f"R$ {g['current_amount']:,.2f} / R$ {g['target_amount']:,.2f}",
                pct_str,
                status_display,
                d_str,
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Erro ao listar metas: {e}[/]")


@goals.command()
@click.argument("goal_id", type=int)
@click.argument("amount", type=float)
def contribute(goal_id, amount):
    """Adiciona valor a uma meta."""
    try:
        with console.status("[bold green]Atualizando meta..."):
            goal = personal_finance_agent.contribute_to_goal(goal_id, amount)

        console.print(f"[green]R$ {amount:,.2f} adicionado a meta '{goal['name']}'[/]")
        console.print(f"   Progresso: R$ {goal['current_amount']:,.2f} / R$ {goal['target_amount']:,.2f}")

        if goal["status"] == "completed":
            console.print("[bold green]Parabens! Meta atingida![/]")

    except Exception as e:
        console.print(f"[red]Erro: {e}[/]")


@goals.command()
@click.argument("goal_id", type=int)
def goal_analyze(goal_id):
    """Analisa meta com cenarios e sugestao da IA."""
    try:
        with console.status("[bold green]Analisando meta..."):
            analysis = personal_finance_agent.analyze_goal(goal_id)

        console.print(f"\n[bold cyan]Analise da Meta: {analysis['name']}[/]\n")

        # Progress bar
        pct = analysis.get("progress_percent", 0)
        bar_width = 40
        filled = int(bar_width * pct / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        console.print(f"  Progresso: [{bar}] {pct:.1f}%")
        console.print(f"  Acumulado: R$ {analysis['current_amount']:,.2f} de R$ {analysis['target_amount']:,.2f}")
        console.print()

        # Scenarios
        if "scenarios" in analysis:
            sc_table = Table(box=box.ROUNDED, title="Cenarios de Projecao")
            sc_table.add_column("Cenario", style="cyan")
            sc_table.add_column("Valor Mensal", style="white", justify="right")
            sc_table.add_column("Previsao", style="yellow")
            for sc_name, sc_data in analysis["scenarios"].items():
                sc_table.add_row(
                    sc_name.capitalize(),
                    format_currency(sc_data.get("monthly", 0), "BRL"),
                    sc_data.get("prediction", "-"),
                )
            console.print(sc_table)
            console.print()

        # AI suggestion
        ai_text = analysis.get("ai_suggestion")
        if ai_text:
            console.print(Panel(str(ai_text), title="Sugestao da IA", border_style="green"))

    except Exception as e:
        console.print(f"[red]Erro ao analisar meta: {e}[/]")


# ====== COMMAND: alerts ======
@click.group()
def alerts():
    """🔔 Alertas inteligentes."""
    pass


@alerts.command()
def check():
    """Verifica e gera alertas automaticamente."""
    try:
        with console.status("[bold green]Verificando alertas..."):
            new_alerts = personal_finance_agent.check_alerts()

        if new_alerts:
            console.print(f"[green]{len(new_alerts)} novo(s) alerta(s) gerado(s):[/]")
            for a in new_alerts:
                icon = "🔴" if a["severity"] == "high" else "🟡" if a["severity"] == "medium" else "🟢"
                console.print(f"  {icon} [{a['alert_type']}] {a['title']}")
        else:
            console.print("[green]Nenhum novo alerta necessario.[/]")

    except Exception as e:
        console.print(f"[red]Erro ao verificar alertas: {e}[/]")


@alerts.command(name="list")
@click.option("--all", "-a", "show_all", is_flag=True, help="Mostrar tambem alertas ja dispensados")
def list_alerts(show_all):
    """Lista alertas."""
    try:
        with console.status("[bold green]Buscando alertas..."):
            alert_list = personal_finance_agent.list_alerts(active_only=not show_all)

        if not alert_list:
            console.print("[green]Nenhum alerta pendente.[/]")
            return

        table = Table(box=box.ROUNDED, title="Alertas")
        table.add_column("ID", style="dim", justify="right")
        table.add_column("Tipo", style="cyan")
        table.add_column("Mensagem", style="white")
        table.add_column("Severidade", style="yellow")
        table.add_column("Data", style="white")

        for a in alert_list:
            sev_icon = "🔴" if a["severity"] == "high" else "🟡" if a["severity"] == "medium" else "🟢"
            d = a.get("created_at", "")
            d_str = d.strftime("%d/%m/%Y %H:%M") if hasattr(d, "strftime") else str(d)[:16]
            table.add_row(
                str(a["id"]),
                a.get("alert_type", "-"),
                a.get("title", "-")[:60],
                f"{sev_icon} {a['severity']}",
                d_str,
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Erro ao listar alertas: {e}[/]")


@alerts.command()
@click.argument("alert_id", type=int)
def dismiss(alert_id):
    """Dispensa um alerta."""
    try:
        success = personal_finance_agent.dismiss_alert(alert_id)
        if success:
            console.print(f"[green]Alerta {alert_id} dispensado.[/]")
        else:
            console.print(f"[red]Alerta {alert_id} nao encontrado.[/]")

    except Exception as e:
        console.print(f"[red]Erro: {e}[/]")


# ====== MAIN CLI ======
@click.group(invoke_without_command=True)
@click.option("--version", "-v", "version_flag", is_flag=True, help="Mostrar versão")
@click.pass_context
def cli(ctx, version_flag: bool):
    """🚀 Stonks AI - Assistente financeiro inteligente via terminal."""
    try:
        if version_flag:
            console.print(f"Stonks AI v{__version__}")
            return

        if ctx.invoked_subcommand is None:
            print_banner()
            console.print("[bold]Comandos disponíveis:[/]")
            console.print("  [cyan]quote TICKER[/]        → Cotação atual")
            console.print("  [cyan]history TICKER[/]       → Histórico e gráfico")
            console.print("  [cyan]analyze TICKER[/]       → Análise completa com IA")
            console.print("  [cyan]compare TICKERS...[/]   → Comparar ações")
            console.print("  [cyan]watchlist[/]            → Gerenciar watchlist")
            console.print("  [cyan]chat PERGUNTA[/]        → Chat financeiro com IA")
            console.print("  [cyan]finance COMANDO[/]      → Finanças pessoais")
            console.print("  [cyan]goals COMANDO[/]        → Metas financeiras")
            console.print("  [cyan]alerts COMANDO[/]       → Alertas inteligentes")
            console.print("  [cyan]init[/]                 → Inicializar sistema")
            console.print("  [cyan]config[/]               → Configurações")
            console.print("\nExemplos:")
            console.print("  stonks quote PETR4")
            console.print("  stonks quote AAPL -e NYSE")
            console.print("  stonks analyze VALE3")
            console.print("  stonks chat 'O que é P/L?'")
            console.print("  stonks chat -i")
            console.print("\nUse [cyan]stonks COMANDO --help[/] para detalhes.")
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Operação cancelada pelo usuário.[/]")
        return


# ====== Registra comandos ======
cli.add_command(quote)
cli.add_command(history)
cli.add_command(analyze)
cli.add_command(compare)
cli.add_command(watchlist)
cli.add_command(chat)
cli.add_command(init)
cli.add_command(config_cmd)
cli.add_command(version)
cli.add_command(finance)
cli.add_command(goals)
cli.add_command(alerts)


if __name__ == "__main__":
    cli()
