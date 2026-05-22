# Referência de Comandos

## Uso Geral

```bash
stonks [OPTIONS] COMMAND [ARGS]...
```

### Opções Globais

| Opção | Descrição |
|-------|-----------|
| `--version`, `-v` | Mostra versão |
| `--help` | Mostra ajuda |

---

## 📊 quote — Cotação Atual

```bash
stonks quote TICKER [--exchange B3|NYSE]
```

| Argumento | Descrição |
|-----------|-----------|
| `TICKER` | Código do ativo (ex: PETR4, AAPL) |
| `--exchange`, `-e` | Forçar bolsa: `B3` ou `NYSE` |

**Exemplos:**
```bash
stonks quote PETR4
stonks quote AAPL -e NYSE
stonks quote VALE3
stonks quote WEGE3
```

---

## 📈 history — Histórico de Preços

```bash
stonks history TICKER [--exchange B3|NYSE] [--period 3mo] [--chart/--no-chart]
```

| Opção | Descrição | Padrão |
|-------|-----------|--------|
| `--exchange`, `-e` | Forçar bolsa | Auto-detect |
| `--period`, `-p` | Período: `1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, `max` | `1mo` |
| `--chart/--no-chart` | Exibir gráfico no terminal | `True` (chart) |

O gráfico mostra a evolução do preço de fechamento no período selecionado, com tabela dos últimos 15 pregões, média do período e variação total.

**Exemplos:**
```bash
stonks history PETR4
stonks history AAPL -e NYSE --period 1y
stonks history VALE3 --chart
stonks history TSLA -e NYSE --period 6mo --no-chart
```

---

## 🔍 analyze — Análise Completa com IA

```bash
stonks analyze TICKER [--exchange B3|NYSE]
```

| Opção | Descrição |
|-------|-----------|
| `--exchange`, `-e` | Forçar bolsa (auto-detect se omitido) |

Requer **Ollama** rodando e modelo baixado. Se não disponível, mostra apenas dados fundamentalistas.

**Exemplos:**
```bash
stonks analyze PETR4
stonks analyze AAPL -e NYSE
stonks analyze BBAS3
```

---

## ⚖️ compare — Comparar Ações

```bash
stonks compare TICKER [TICKER ...]
```

Compara múltiplos ativos lado a lado.

**Exemplos:**
```bash
stonks compare PETR4 VALE3
stonks compare AAPL MSFT GOOGL -e NYSE
stonks compare PETR4 VALE3 BBAS3 WEGE3
```

---

## 👀 watchlist — Gerenciar Watchlist

```bash
stonks watchlist [--add TICKER] [--remove TICKER] [--exchange B3|NYSE] [--name "Nome"]
```

| Opção | Descrição |
|-------|-----------|
| `--add`, `-a` | Adicionar ativo |
| `--remove`, `-r` | Remover ativo |
| `--exchange`, `-e` | Bolsa do ativo |
| `--name`, `-n` | Nome amigável |

**Exemplos:**
```bash
stonks watchlist                               # Listar
stonks watchlist --add PETR4                   # Adicionar
stonks watchlist --add AAPL -e NYSE -n "Apple"
stonks watchlist --remove PETR4                # Remover
```

---

## 💬 chat — Chat Financeiro com IA

```bash
stonks chat PERGUNTA [--interactive]
```

Chat interativo para tirar dúvidas sobre investimentos, indicadores, estratégias e economia.

| Opção | Descrição |
|-------|-----------|
| `--interactive`, `-i` | Modo conversa contínua |

**Exemplos:**
```bash
stonks chat "O que é P/L?"
stonks chat "Qual a diferença entre CDB e Tesouro Direto?"
stonks chat -i                               # Modo interativo
```

---

## ⚙️ init — Inicializar Sistema

```bash
stonks init
```

Cria diretório de configuração, banco de dados SQLite, arquivo `config.yaml` padrão, categorias padrão de finanças pessoais e configurações de alerta.

---

## 🔧 config — Configurações

```bash
stonks config [--show] [--set KEY VALUE]
```

| Opção | Descrição |
|-------|-----------|
| `--show`, `-s` | Exibir configuração atual |
| `--set`, `-S` | Alterar configuração: `llm.model llama3.2:1b` |

**Exemplos:**
```bash
stonks config --show
stonks config --set llm.model llama3.2:1b
stonks config --set ui.language en-US
```

---

## 💰 finance — Finanças Pessoais

```bash
stonks finance COMANDO [ARGS]...
```

Grupo de comandos para gerenciamento de finanças pessoais: dashboard, transações, importação de extratos e categorias.

### finance dashboard

```bash
stonks finance dashboard [--year ANO] [--month MES] [--ai]
```

| Opção | Descrição |
|-------|-----------|
| `--year`, `-y` | Ano (ex: 2025) |
| `--month`, `-m` | Mês (1-12) |
| `--ai` | Incluir resumo com IA |

Mostra resumo financeiro do mês: receitas, despesas, saldo, média diária, categorias com mais gastos, metas ativas e alertas.

**Exemplos:**
```bash
stonks finance dashboard
stonks finance dashboard --year 2025 --month 3
stonks finance dashboard --ai              # Com análise da IA
```

### finance import

```bash
stonks finance import FILE_PATH
```

Importa transações de extrato bancário. Suporta formatos **CSV**, **Excel** (.xlsx/.xls) e **PDF**.

**Exemplos:**
```bash
stonks finance import extrato_nubank.csv
stonks finance import extrato_itau.xlsx
stonks finance import fatura_cartao.pdf
```

### finance transactions

```bash
stonks finance transactions [--limit N] [--type expense|income] [--days N] [--category ID]
```

| Opção | Descrição | Padrão |
|-------|-----------|--------|
| `--limit`, `-l` | Máximo de transações | 50 |
| `--type`, `-t` | Filtrar por tipo: `expense` ou `income` | Todos |
| `--days`, `-d` | Filtrar por dias recentes | Todos |
| `--category`, `-c` | Filtrar por ID da categoria | Todas |

**Exemplos:**
```bash
stonks finance transactions
stonks finance transactions --limit 10
stonks finance transactions --type expense --days 30
```

### finance add

```bash
stonks finance add DESCRIÇÃO VALOR [--date DATA] [--type expense|income] [--category CATEGORIA] [--notes OBS]
```

Adiciona transação manualmente com categorização automática.

**Exemplos:**
```bash
stonks finance add "Salário" 5000 --type income --date 2025-01-15
stonks finance add "Ifood" 45.90 --category Alimentação
stonks finance add "Netflix" 55.90 --type expense --category Assinaturas
```

### finance recategorize

```bash
stonks finance recategorize TRANSACTION_ID NOVA_CATEGORIA
```

Reclassifica uma transação. O categorizador aprende com a reclassificação para melhorar classificações futuras.

**Exemplos:**
```bash
stonks finance recategorize 42 Alimentação
stonks finance recategorize 15 Transporte
```

### finance delete

```bash
stonks finance delete TRANSACTION_ID
```

Remove uma transação.

**Exemplos:**
```bash
stonks finance delete 42
```

### finance categories

```bash
stonks finance categories
```

Lista todas as categorias disponíveis com seus ícones e limites de orçamento.

**Exemplos:**
```bash
stonks finance categories
```

---

## 🎯 goals — Metas Financeiras

```bash
stonks goals COMANDO [ARGS]...
```

Grupo de comandos para gerenciamento de metas financeiras.

### goals create

```bash
stonks goals create NOME VALOR_ALVO [--deadline DATA] [--type savings|debt|investment|custom] [--priority low|medium|high] [--description DESCRICAO]
```

**Exemplos:**
```bash
stonks goals create "Reserva de Emergência" 10000 --deadline 2025-12-31 --type savings --priority high
stonks goals create "Viagem" 5000 --deadline 2025-06-30 --priority medium
stonks goals create "Quitar Dívida" 3000 --type debt --priority high
```

### goals list

```bash
stonks goals list [--status active|completed|all]
```

| Opção | Descrição | Padrão |
|-------|-----------|--------|
| `--status`, `-s` | Filtrar por status | `active` |

**Exemplos:**
```bash
stonks goals list
stonks goals list --status all
stonks goals list --status completed
```

### goals contribute

```bash
stonks goals contribute GOAL_ID VALOR
```

Adiciona valor a uma meta. Se o valor acumulado atingir o alvo, a meta é marcada como concluída.

**Exemplos:**
```bash
stonks goals contribute 1 500
stonks goals contribute 2 200
```

### goals analyze

```bash
stonks goals analyze GOAL_ID
```

Analisa meta com projeções de cenários e sugestão da IA (se disponível).

**Exemplos:**
```bash
stonks goals analyze 1
```

---

## 🔔 alerts — Alertas Inteligentes

```bash
stonks alerts COMANDO [ARGS]...
```

Grupo de comandos para alertas financeiros inteligentes.

### alerts check

```bash
stonks alerts check
```

Verifica automaticamente padrões de gastos, saldo baixo, orçamentos estourados, mudanças em assinaturas e metas em risco.

**Exemplos:**
```bash
stonks alerts check
```

### alerts list

```bash
stonks alerts list [--all]
```

Lista alertas ativos (ou todos com `--all`).

**Exemplos:**
```bash
stonks alerts list
stonks alerts list --all
```

### alerts dismiss

```bash
stonks alerts dismiss ALERT_ID
```

Dispensa um alerta.

**Exemplos:**
```bash
stonks alerts dismiss 1
```

---

## ℹ️ version — Versão

```bash
stonks --version
stonks version
```

Mostra a versão instalada do Stonks AI.
