<div align="center">

# 🚀 Stonks AI

**Assistente Financeiro Inteligente — 100% Local, Privacidade Primeiro**

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-0.1.0-blueviolet)](https://pypi.org/project/stonks-ai/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Made with ❤️](https://img.shields.io/badge/Made%20with-%E2%9D%A4%EF%B8%8F-red)](https://github.com/miguel7p/stonks-ai)

---

**Stonks AI** é um assistente financeiro inteligente que roda **inteiramente na sua máquina** — sem envio de dados para nuvem, sem telemetria, sem rastreadores. Consulta cotações da **B3 🇧🇷** e **NYSE/Nasdaq 🇺🇸**, faz análises com **IA local via Ollama**, e gerencia suas **finanças pessoais** importando extratos bancários.

</div>

---

## ✨ Funcionalidades

| Categoria | Capacidades |
|-----------|-------------|
| 📊 **Cotações em Tempo Real** | Preço, variação, máx/mín, abertura e fechamento anterior — B3 e NYSE/Nasdaq |
| 📈 **Dados Históricos** | Séries temporais com gráficos ASCII no terminal |
| 🤖 **Análise com IA Local** | Análise técnica e fundamentalista via Ollama (Llama 3, Mistral, Gemma) |
| ⚖️ **Comparação de Ativos** | Compare múltiplos ativos lado a lado |
| 👀 **Watchlist** | Gerencie sua lista de ativos monitorados |
| 💰 **Finanças Pessoais** | Importe extratos de CSV, Excel e PDF; categorize despesas automaticamente |
| 🎯 **Metas Financeiras** | Acompanhe objetivos de curto, médio e longo prazo |
| 📊 **Interface Web** | Dashboard interativo com Streamlit + Plotly |
| 📁 **Histórico Persistente** | Todas as consultas salvas em banco SQLite local |
| 🛡️ **Tratamento Estruturado de Erros** | Matriz de erros com 34 códigos e soluções documentadas |

---

## 🚀 Quick Start

```bash
# 1. Instalar
pip install stonks-ai

# 2. Baixar modelo LLM (opcional, para análise com IA)
ollama pull llama3.2:3b

# 3. Inicializar o sistema
stonks init

# 4. Consultar cotações!
stonks quote PETR4
stonks analyze VALE3
stonks compare PETR4 VALE3
```

---

## 📦 Instalação Detalhada

Consulte o [`docs/INSTALACAO.md`](docs/INSTALACAO.md) para instruções passo a passo em **Windows**, **Linux** e **macOS**, incluindo:

- Configuração de ambiente virtual
- Instalação do Ollama e download de modelos
- Resolução de dependências opcionais (Selenium, ChromeDriver)
- Ativação do WAL mode no SQLite para melhor performance

**Pré-requisitos:** Python 3.11+ e [Ollama](https://ollama.com/) (opcional, para análises com IA).

---

## ⌨️ CLI - Uso Principal

| Comando | Descrição | Exemplo |
|---------|-----------|---------|
| `stonks quote TICKER` | Cotação em tempo real | `stonks quote PETR4` |
| `stonks history TICKER` | Histórico com gráfico ASCII | `stonks history AAPL -e NYSE --chart` |
| `stonks analyze TICKER` | Análise completa com IA local | `stonks analyze VALE3` |
| `stonks compare TICKERS...` | Comparação de ativos | `stonks compare PETR4 VALE3` |
| `stonks watchlist` | Gerenciar watchlist | `stonks watchlist --add PETR4` |
| `stonks finance` | Finanças pessoais | `stonks finance import --file extrato.csv` |
| `stonks goals` | Metas financeiras | `stonks goals --add "Viagem 2026" 15000` |
| `stonks init` | Inicializar sistema e banco | `stonks init` |
| `stonks config` | Exibir/alterar configurações | `stonks config --show` |

Para a referência completa de todos os comandos e subcomandos, veja [`docs/COMANDOS.md`](docs/COMANDOS.md).

---

## 🌐 Interface Web

Além da CLI, o Stonks AI oferece uma **interface web interativa** construída com **Streamlit** e **Plotly**:

```bash
streamlit run webapp/app.py
```

O dashboard web inclui:

- 📊 **Gráficos interativos** de cotações e histórico
- 🔍 **Análise visual** de múltiplos ativos
- 💰 **Painel de finanças pessoais** com gráficos de categorização
- 📱 Layout responsivo para dispositivos móveis

---

## 🔧 Configuração

O arquivo de configuração em YAML é criado automaticamente ao executar `stonks init`:

```yaml
database:
  path: ~/.stonks_ai/data/stonks_ai.db

llm:
  model: llama3.2:3b
  endpoint: http://localhost:11434
  temperature: 0.3
  max_tokens: 2048
  timeout: 30

ui:
  language: pt-BR
  theme: dark
```

Para todas as opções disponíveis, veja [`docs/CONFIGURACAO.md`](docs/CONFIGURACAO.md).

---

## 📚 Exemplos de Uso

| Comando | Descrição |
|---------|-----------|
| `stonks quote PETR4` | Cotação atual da Petrobrás (B3) |
| `stonks history AAPL -e NYSE --period 6mo` | Histórico da Apple nos últimos 6 meses |
| `stonks analyze VALE3 --full` | Análise fundamentalista + técnica completa |
| `stonks compare PETR4 VALE3 ITUB4` | Comparar três ativos da B3 |
| `stonks finance import --file extrato.pdf` | Importar fatura de cartão em PDF |
| `stonks finance budget --set "Alimentação" 1200` | Definir orçamento mensal |

Mais exemplos detalhados em [`docs/EXEMPLOS.md`](docs/EXEMPLOS.md).

---

## 🏗️ Arquitetura

O Stonks AI segue uma arquitetura **local-first** com padrão de **Agentes**:

```
                    ┌──────────────┐
                    │   Usuário     │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
         ┌────▼────┐ ┌────▼────┐ ┌────▼────┐
         │   CLI   │ │  Web    │ │  API    │
         │ (Click  │ │(Stream- │ │(Interna)│
         │ + Rich) │ │ lit)    │ │         │
         └────┬────┘ └────┬────┘ └────┬────┘
              │            │            │
              └────────────┼────────────┘
                           │
              ┌────────────▼────────────┐
              │     Agentes (ABC)       │
              │  ┌───────────────────┐  │
              │  │ FinancialAgent    │  │
              │  │ PersonalFinance   │  │
              │  │    Agent          │  │
              │  └───────────────────┘  │
              └────────────┬────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
  ┌─────▼──────┐  ┌───────▼───────┐  ┌───────▼───────┐
  │ Collectors │  │  LLM (Ollama) │  │   Models      │
  │ B3 / NYSE  │  │  Local LLM    │  │  SQLAlchemy   │
  │ CSV/Excel/ │  │  llama3.2:3b  │  │  2.0 ORM      │
  │   PDF      │  │               │  │               │
  └────────────┘  └───────────────┘  └───────┬───────┘
                                             │
                                      ┌──────▼──────┐
                                      │   SQLite    │
                                      │  (WAL mode) │
                                      └─────────────┘
```

- **BaseAgent (ABC)** → [`FinancialAgent`](stonks_ai/agents/financial_agent.py) + [`PersonalFinanceAgent`](stonks_ai/agents/personal_finance_agent.py)
- **Coletores modulares** para B3, NYSE/Nasdaq, e importação financeira (CSV, Excel, PDF)
- **Cliente LLM** genérico para Ollama com sistema de prompts versionados
- **SQLite + SQLAlchemy 2.0** com WAL mode para performance
- **Configuração centralizada** em [`data/config.yaml`](data/config.yaml)

---

## 📁 Estrutura do Projeto

```
stonks-ai/
├── stonks_ai/                    # Código-fonte principal
│   ├── main.py                   # CLI (Click + Rich)
│   ├── config.py                 # Gerenciamento de configuração YAML
│   ├── database.py               # SQLite + SQLAlchemy 2.0 (WAL mode)
│   ├── agents/                   # Agentes de IA (padrão ABC)
│   │   ├── base_agent.py         # Classe abstrata base
│   │   ├── financial_agent.py    # Agente de análise financeira
│   │   └── personal_finance_agent.py  # Agente de finanças pessoais
│   ├── collectors/               # Coletores de dados
│   │   ├── stocks/               # B3, NYSE/Nasdaq, Fundamentus
│   │   └── finance/              # Importação CSV, Excel, PDF
│   ├── llm/                      # Cliente Ollama + Prompts
│   │   ├── client.py             # Cliente HTTP para Ollama
│   │   └── prompts.py            # Templates de prompt versionados
│   ├── models/                   # Modelos ORM (SQLAlchemy)
│   │   ├── stock_history.py
│   │   ├── transaction.py
│   │   ├── category.py
│   │   ├── financial_goal.py
│   │   ├── watchlist.py
│   │   ├── alert.py
│   │   └── user_preferences.py
│   └── utils/                    # Utilitários
│       ├── charts.py             # Gráficos ASCII (plotext)
│       ├── formatters.py         # Formatadores de moeda/data
│       ├── validators.py         # Validadores de ticker, valores
│       └── finance_utils.py      # Cálculos financeiros
├── webapp/                       # Interface web
│   └── app.py                    # Streamlit + Plotly dashboard
├── tests/                        # Suíte de testes (pytest)
│   ├── test_agents.py
│   ├── test_cli.py
│   ├── test_collectors.py
│   ├── test_config.py
│   ├── test_database.py
│   ├── test_llm.py
│   └── test_validators.py
└── docs/                         # Documentação completa
    ├── adr.md                    # Architecture Decision Records
    ├── API.md                    # Referência da API interna
    ├── COMANDOS.md               # Referência de comandos CLI
    ├── CONFIGURACAO.md           # Guia de configuração
    ├── EXEMPLOS.md               # Exemplos de uso
    ├── INSTALACAO.md             # Guia de instalação
    └── TROUBLESHOOTING.md        # Matriz de erros
```

---

## 🛠️ Tech Stack

| Tecnologia | Versão | Finalidade |
|------------|--------|------------|
| [Python](https://www.python.org/) | 3.11+ | Linguagem principal |
| [Click](https://click.palletsprojects.com/) | 8.1+ | Framework CLI |
| [Rich](https://rich.readthedocs.io/) | 13.0+ | Terminal com formatação |
| [SQLAlchemy](https://www.sqlalchemy.org/) | 2.0+ | ORM e migrações |
| [SQLite](https://www.sqlite.org/) | — | Banco de dados local (WAL mode) |
| [yfinance](https://github.com/ranaroussi/yfinance) | 0.2+ | Dados NYSE/Nasdaq |
| [Ollama](https://ollama.com/) | — | Inferência LLM local |
| [Streamlit](https://streamlit.io/) | 1.57+ | Dashboard web |
| [Plotly](https://plotly.com/python/) | 6.0+ | Gráficos interativos |
| [pydantic](https://docs.pydantic.dev/) | 2.0+ | Validação de dados |
| [pytest](https://docs.pytest.org/) | 7.0+ | Testes automatizados |
| [pytesseract](https://github.com/madmaze/pytesseract) | — | OCR para PDFs escaneados |

---

## 📖 Documentação

| Documento | Descrição |
|-----------|-----------|
| [`docs/INSTALACAO.md`](docs/INSTALACAO.md) | Guia de instalação detalhado para Windows, Linux e macOS |
| [`docs/COMANDOS.md`](docs/COMANDOS.md) | Referência completa de todos os comandos CLI |
| [`docs/CONFIGURACAO.md`](docs/CONFIGURACAO.md) | Todas as opções de configuração do YAML |
| [`docs/EXEMPLOS.md`](docs/EXEMPLOS.md) | Exemplos práticos de uso |
| [`docs/API.md`](docs/API.md) | Documentação da API interna para uso programático |
| [`docs/adr.md`](docs/adr.md) | Architecture Decision Records (12 ADRs documentados) |
| [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) | Matriz de erros com 34 códigos e soluções |

---

## 🧪 Testes

```bash
# Executar todos os testes
pytest

# Com relatório de cobertura
pytest --cov=stonks_ai --cov-report=term-missing

# Testes específicos por módulo
pytest tests/test_collectors.py -v
pytest tests/test_agents.py -v

# Modo verboso com output detalhado
pytest -v --tb=long
```

---

## 🗺️ Roadmap

- [ ] **Suporte a Criptomoedas** — Integração com CoinGecko e CoinMarketCap
- [ ] **Notificações em Tempo Real** — Alertas de preço alvo via desktop/email
- [ ] **Relatório Periódico de Carteira** — Resumo automático por período
- [ ] **Integração com Corretoras** — API para consulta de posições e geração de ordens
- [ ] **Interface TUI** — Modo texto interativo com [Textual](https://textual.textualize.io/)
- [ ] **Modo Servidor (API REST)** — Endpoint HTTP para integração com outros sistemas
- [ ] **Exportação de Relatórios** — Geração de relatórios em PDF e Excel
- [ ] **Multi-idioma** — Suporte a inglês e espanhol na interface
- [ ] **Plugins** — Sistema de extensões para coletores e análises personalizadas

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Para contribuir:

1. Faça um **fork** do repositório
2. Crie uma **branch** para sua feature: `git checkout -b feat/nova-funcionalidade`
3. Faça **commit** das suas alterações: `git commit -m 'feat: adiciona nova funcionalidade'`
4. Envie para o **branch**: `git push origin feat/nova-funcionalidade`
5. Abra um **Pull Request**

**Diretrizes:**
- Siga o estilo de código definido pelo **Black** (line-length=100) e **Ruff**
- Escreva **testes** para novas funcionalidades
- Mantenha a **cobertura de testes** existente
- Atualize a **documentação** quando necessário
- Use **conventional commits** (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`)

```bash
# Configurar ambiente de desenvolvimento
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows
pip install -e ".[dev]"
pre-commit install
```

---

## 📄 Licença

Distribuído sob a licença **MIT**. Veja o arquivo [`LICENSE`](LICENSE) para mais informações.

---

<div align="center">

**Stonks AI** — Feito com ❤️ para a comunidade financeira brasileira

[Relatar Bug](https://github.com/miguel7p/stonks-ai/issues) · [Solicitar Feature](https://github.com/miguel7p/stonks-ai/issues) · [Discutir](https://github.com/miguel7p/stonks-ai/discussions)

</div>
