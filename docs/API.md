# Documentação da API Interna

## Visão Geral

O Stonks AI pode ser usado programaticamente importando seus módulos principais.

---

## 📦 Importação

```python
from stonks_ai.agents.financial_agent import FinancialAgent
from stonks_ai.agents.personal_finance_agent import PersonalFinanceAgent
from stonks_ai.config import Config, config
from stonks_ai.database import Database, db
from stonks_ai.llm.client import OllamaClient, llm_client
```

---

## 🏦 FinancialAgent

Agente para análise de ações (B3 e NYSE/Nasdaq).

```python
agent = FinancialAgent()

# Cotação
quote = agent.get_quote("PETR4")
print(f"{quote.ticker}: R$ {quote.price:.2f} ({quote.change_percent:+.2f}%)")

# Cotação com exchange explícita
quote = agent.get_quote("AAPL", exchange="NYSE")
print(f"{quote.ticker}: $ {quote.price:.2f}")

# Histórico
history = agent.get_history("VALE3", period="6mo")
for entry in history.data[:5]:
    print(f"{entry['date']}: {entry['close']}")

# Dados fundamentalistas
funds = agent.get_fundamentals("PETR4")
if funds:
    print(f"P/L: {funds.pe_ratio}, DY: {funds.dividend_yield}%")

# Análise completa com IA
result = agent.analyze("WEGE3")
print(result["analysis"])  # Texto gerado pelo LLM

# Comparação
result = agent.compare(["PETR4", "VALE3", "ITUB4"])
print(result["comparison"])
```

### Métodos

| Método | Retorno | Descrição |
|--------|---------|-----------|
| `get_quote(ticker, exchange=None)` | `StockQuote` | Cotação atual |
| `get_history(ticker, exchange=None, period="3mo", interval="1d")` | `StockHistory` | Dados históricos |
| `get_fundamentals(ticker, exchange=None)` | `StockFundamentals \| None` | Indicadores fundamentalistas |
| `analyze(ticker, exchange=None)` | `Dict` | Análise completa com IA |
| `compare(tickers)` | `Dict` | Comparação entre ativos |

### Dataclasses

```python
@dataclass
class StockQuote:
    ticker: str
    exchange: str
    price: float
    change: float
    change_percent: float
    high: float
    low: float
    open_price: float
    previous_close: float
    volume: int
    currency: str
    name: str
    timestamp: str

@dataclass
class StockHistory:
    ticker: str
    exchange: str
    period: str
    interval: str
    data: List[Dict]

@dataclass
class StockFundamentals:
    ticker: str
    name: str
    sector: Optional[str]
    market_cap: Optional[float]
    pe_ratio: Optional[float]
    dividend_yield: Optional[float]
    eps: Optional[float]
    beta: Optional[float]
    pb_ratio: Optional[float]
    roe: Optional[float]
    net_margin: Optional[float]
    debt_equity: Optional[float]
    revenue: Optional[float]
    net_income: Optional[float]
    free_cash_flow: Optional[float]
```


## ⚙️ Gerenciamento de Configuração

```python
from stonks_ai.config import config

# Ler configuração
model = config.get("llm", "model")  # "llama3.2:3b"
db_path = config.db_path  # Path object

# Alterar configuração
config.set("mistral:7b", "llm", "model")
config.save()

# Propriedades
print(config.db_path)       # Caminho do banco
print(config.llm_model)     # Modelo atual
print(config.llm_endpoint)  # Endpoint Ollama
```

---

## 🗄️ Banco de Dados

```python
from stonks_ai.database import db, DatabaseError

# Inicializar
db.initialize()

# Operações com session
from stonks_ai.models.watchlist import WatchlistItem

with db.session() as session:
    # Adicionar
    item = WatchlistItem(ticker="PETR4", exchange="B3", name="Petrobras")
    session.add(item)

    # Query
    items = session.query(WatchlistItem).all()
    for item in items:
        print(f"{item.ticker} - {item.name}")

# Health check
if db.health_check():
    print("Banco OK")
```

---

## 🤖 Cliente LLM (Ollama)

```python
from stonks_ai.llm.client import llm_client, LLMError

# Verificar disponibilidade
if llm_client.is_available():
    print("Ollama disponível!")
    models = llm_client.available_models
    print(f"Modelos: {[m['name'] for m in models]}")

# Geração simples
response = llm_client.generate("Analise a PETR4")
print(response)

# Geração com system prompt
response = llm_client.generate(
    "Qual o P/L da VALE3?",
    system_prompt="Você é um analista financeiro.",
)

# Geração estruturada (JSON)
result = llm_client.generate_structured(
    "Analise AAPL", output_format="json"
)

# Streaming
async for chunk in llm_client.generate_stream("Explique o que é P/L"):
    print(chunk, end="")
```

---

## 💰 PersonalFinanceAgent

Agente para gerenciamento de finanças pessoais: transações, importação, categorização, metas e alertas.

```python
from stonks_ai.agents.personal_finance_agent import PersonalFinanceAgent

agent = PersonalFinanceAgent()

# Inicializar módulo (cria categorias e alertas padrão)
result = agent.initialize()
print(f"{result['categories']} categorias criadas")
```

### Transações

```python
# Adicionar transação manual
tx = agent.add_transaction(
    description="Ifood - Hamburguer",
    amount=45.90,
    tx_type="expense",
)
print(f"Transação: {tx['description']} - R$ {tx['amount']:.2f} ({tx['category_name']})")

# Listar transações com filtros
transactions = agent.list_transactions(
    limit=20,
    transaction_type="expense",  # expense ou income
    days=30,                      # últimos 30 dias
    category_id=1,                # filtrar por categoria
)
for tx in transactions:
    print(f"{tx['date']} | {tx['description']} | R$ {tx['amount']:.2f}")

# Buscar transação específica
tx = agent.get_transaction(transaction_id=42)
if tx:
    print(f"{tx['description']}: R$ {tx['amount']:.2f}")

# Atualizar transação
updated = agent.update_transaction(
    transaction_id=42,
    description="Ifood - Hamburguer X",
    category_name="Alimentação",
)

# Reclassificar (com aprendizado automático)
agent.update_transaction_category(
    transaction_id=42,
    new_category_name="Alimentação",
)

# Deletar transação
agent.delete_transaction(transaction_id=42)
```

### Importação de Extratos

```python
# Importar extrato bancário (CSV, Excel, PDF)
result = agent.import_file("extrato_nubank.csv")
print(f"Importadas: {result['imported']}")
print(f"Duplicatas: {result['duplicates']}")
print(f"Erros: {result['errors']}")

# Suporta .csv, .xlsx, .xls, .pdf
# Formatos de banco detectados automaticamente:
# Nubank, Inter, C6 Bank, Itaú, Bradesco, Santander
```

### Dashboard e Resumo Mensal

```python
# Dashboard financeiro completo
dashboard = agent.get_dashboard(year=2025, month=1)
print(f"Receitas: R$ {dashboard['summary']['total_income']:.2f}")
print(f"Despesas: R$ {dashboard['summary']['total_expense']:.2f}")
print(f"Saldo: R$ {dashboard['summary']['balance']:.2f}")

# Categorias com mais gastos
for cat in dashboard['summary']['top_categories']:
    print(f"  {cat['name']}: R$ {cat['amount']:.2f} ({cat['percent']}%)")

# Resumo mensal com IA
summary_ai = agent.get_monthly_summary_ai(year=2025, month=1)
print(summary_ai)  # Análise em linguagem natural
```

### Metas Financeiras

```python
# Criar meta
goal = agent.create_goal(
    name="Reserva de Emergência",
    target_amount=10000.0,
    deadline="2025-12-31",
    goal_type="savings",
    priority="high",
)
print(f"Meta criada: {goal['name']} - R$ {goal['target_amount']:.2f}")

# Listar metas
goals = agent.list_goals(status="active")
for g in goals:
    print(f"{g['name']}: {g['progress_percent']:.1f}% concluída")

# Contribuir para meta
updated = agent.contribute_to_goal(goal_id=1, amount=500.0)
print(f"Progresso: R$ {updated['current_amount']:.2f} / R$ {updated['target_amount']:.2f}")

# Analisar meta com IA
analysis = agent.analyze_goal(goal_id=1)
print(f"Sugestão: {analysis.get('ai_suggestion', 'N/A')}")

# Atualizar meta
agent.update_goal(goal_id=1, target_amount=15000.0)

# Deletar meta
agent.delete_goal(goal_id=1)
```

### Alertas Inteligentes

```python
# Verificar e gerar alertas
new_alerts = agent.check_alerts()
for a in new_alerts:
    print(f"[{a['severity']}] {a['title']}: {a['message']}")

# Listar alertas ativos
alerts = agent.list_alerts(active_only=True)
for a in alerts:
    print(f"#{a['id']} [{a['alert_type']}] {a['title']}")

# Dispensar alerta
agent.dismiss_alert(alert_id=1)
```

### Categorias

```python
# Listar categorias
categories = agent.list_categories()
for c in categories:
    print(f"{c['icon']} {c['name']}")

# Adicionar categoria personalizada
agent.add_category(
    name="Streaming",
    icon="📺",
    keywords=["NETFLIX", "SPOTIFY", "DISNEY"],
    budget_limit=100.0,
)
```

### Métodos

| Método | Retorno | Descrição |
|--------|---------|-----------|
| `initialize()` | `Dict` | Inicializa categorias e alertas padrão |
| `list_transactions(limit, offset, category_id, transaction_type, days)` | `List[Dict]` | Lista transações com filtros |
| `get_transaction(transaction_id)` | `Dict \| None` | Busca transação por ID |
| `add_transaction(description, amount, date, tx_type, category_name, notes)` | `Dict` | Adiciona transação manual |
| `update_transaction(transaction_id, ...)` | `Dict \| None` | Atualiza transação existente |
| `update_transaction_category(transaction_id, new_category_name)` | `bool` | Reclassifica e aprende |
| `delete_transaction(transaction_id)` | `bool` | Remove transação |
| `import_file(file_path)` | `Dict` | Importa extrato (CSV/Excel/PDF) |
| `get_dashboard(year, month)` | `Dict` | Dashboard financeiro completo |
| `get_monthly_summary_ai(year, month)` | `str` | Resumo mensal com IA |
| `create_goal(name, target_amount, deadline, goal_type, priority, description)` | `Dict` | Cria meta financeira |
| `list_goals(status)` | `List[Dict]` | Lista metas financeiras |
| `contribute_to_goal(goal_id, amount)` | `Dict` | Adiciona valor à meta |
| `update_goal(goal_id, ...)` | `Dict \| None` | Atualiza meta existente |
| `delete_goal(goal_id)` | `bool` | Remove meta |
| `analyze_goal(goal_id)` | `Dict` | Analisa meta com IA |
| `check_alerts()` | `List[Dict]` | Verifica e gera alertas |
| `list_alerts(active_only)` | `List[Dict]` | Lista alertas |
| `dismiss_alert(alert_id)` | `bool` | Dispensa alerta |
| `list_categories()` | `List[Dict]` | Lista categorias |
| `add_category(name, icon, keywords, budget_limit)` | `Dict` | Adiciona categoria |

---

## 📥 Coletores Financeiros

### FinanceImporter (Base)

Classe base abstrata para importação de extratos bancários.

```python
from stonks_ai.collectors.finance.base import FinanceImporter, FinanceDataError

class MeuImporter(FinanceImporter):
    def parse(self, file_path: str) -> List[Dict]:
        # Implementar parsing específico
        pass
```

### CSVImporter

Importa transações de arquivos CSV. Detecta automaticamente o banco pelo nome do arquivo ou cabeçalhos (Nubank, Inter, C6 Bank, Itaú, Bradesco, Santander).

```python
from stonks_ai.collectors.finance.csv_importer import CSVImporter

importer = CSVImporter()
imported, duplicates, errors = importer.import_file("extrato.csv", source="csv")
print(f"{imported} transações importadas")
```

### ExcelImporter

Importa transações de arquivos Excel (.xlsx/.xls). Suporta múltiplas sheets e detecta colunas automaticamente.

```python
from stonks_ai.collectors.finance.excel_importer import ExcelImporter

importer = ExcelImporter()
imported, duplicates, errors = importer.import_file("extrato.xlsx", source="excel")
```

### PDFImporter

Importa transações de extratos em PDF. Usa PyMuPDF (fitz) ou pdfplumber para extrair texto, com fallback para IA (Ollama) em formato não estruturado.

```python
from stonks_ai.collectors.finance.pdf_importer import PDFImporter

importer = PDFImporter()
imported, duplicates, errors = importer.import_file("extrato.pdf", source="pdf")
```

### Categorizer

Classificador automático de transações usando regex + keywords, com fallback para IA e aprendizado por reclassificação.

```python
from stonks_ai.collectors.finance.categorizer import Categorizer

cat = Categorizer()

# Classificar descrição
category_id, category_name = cat.categorize("IFOOD - PEDIDO #1234")
print(f"Categoria: {category_name}")  # "Alimentação"

# Classificar com IA (fallback)
cat_id, cat_name = cat.categorize_with_llm(
    "Assinatura anual de domínio",
    available_categories=[{"id": 1, "name": "Assinaturas"}],
)

# Aprender com reclassificação
cat.learn_from_reclassification(transaction_id=42, new_category_name="Alimentação")

# Inicializar categorias padrão
Categorizer.initialize_default_categories()
```

---

## 📦 Modelos de Dados

### Transaction

```python
from stonks_ai.models.transaction import Transaction

# Campos:
# id, description, amount, type (expense/income),
# category_id, category_name, date, source (manual/csv/excel/pdf),
# source_file, is_recurring, recurring_frequency, recurrence_id,
# notes, tags, created_at
```

### Category

```python
from stonks_ai.models.category import Category, DEFAULT_CATEGORIES

# Categorias padrão: Alimentação, Transporte, Moradia, Assinaturas,
# Saúde, Lazer, Educação, Salário, Transferências, Investimentos, Outros

# Campos:
# id, name, icon, keywords (JSON list), parent_id,
# budget_limit (centavos), budget_period, color, sort_order
```

### FinancialGoal

```python
from stonks_ai.models.financial_goal import FinancialGoal

# Campos:
# id, name, description, target_amount, current_amount,
# deadline, goal_type (savings/debt/purchase/emergency),
# priority (low/medium/high), status (active/completed/cancelled/paused),
# monthly_contribution, ai_suggestion, icon, color

# Propriedades:
# progress_percent  -> float (0-100)
# remaining_amount  -> float
# days_remaining    -> int
# is_on_track       -> bool
```

### Alert

```python
from stonks_ai.models.alert import Alert, AlertConfig, DEFAULT_ALERT_CONFIGS

# Alert - campos:
# id, alert_type, title, message, severity (info/warning/critical),
# category_id, related_transaction_id, related_goal_id,
# data (JSON), read, dismissed, created_at

# Tipos de alerta: spending_pattern, balance_low, budget_exceeded,
# subscription_change, goal_at_risk, unusual_transaction, bill_reminder
```

---

## 📊 Utilitários

```python
from stonks_ai.utils.validators import validate_ticker, detect_exchange
from stonks_ai.utils.formatters import format_currency, format_percent
from stonks_ai.utils.charts import render_line_chart, TerminalChart
from stonks_ai.utils.finance_utils import (
    get_month_summary, get_balance_history,
    get_goal_analysis, check_and_generate_alerts,
)

# Validação
is_valid, msg = validate_ticker("PETR4")
exchange = detect_exchange("AAPL")  # "NYSE"

# Formatação
print(format_currency(1234.56, "BRL"))  # "R$ 1.234,56"
print(format_percent(12.5))             # "+12,50%"
print(format_large_number(1_500_000_000))  # "1,5B"

# Gráficos
chart = TerminalChart()
chart.line_chart(
    data=[100, 102, 105, 103, 108],
    title="PETR4",
    x_labels=["Seg", "Ter", "Qua", "Qui", "Sex"],
)
chart.render()

# Utilitários financeiros
summary = get_month_summary(year=2025, month=1)
balance = get_balance_history(days=90)
goal_analysis = get_goal_analysis(goal_data)
new_alerts = check_and_generate_alerts()
```
