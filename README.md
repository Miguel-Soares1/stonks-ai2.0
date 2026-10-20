<div align="center">

# 🚀 Stonks AI

**Assistente Financeiro Inteligente — 100% Local, Privacidade Primeiro**

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-0.1.0-blueviolet)](https://pypi.org/project/stonks-ai/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Made with ❤️](https://img.shields.io/badge/Made%20with-%E2%9D%A4%EF%B8%8F-red)](https://github.com/stonks-ai/stonks-ai)

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
| 💰 **Finanças Pessoais** | Importe extratos de CSV, Excel e PDF; categorização automática que **aprende quando você corrige** |
| 🔁 **Transações Recorrentes** | Aluguel, salário e assinaturas lançados sozinhos quando a data chega |
| 💡 **Insights do Mês** | Categoria que mais subiu e orçamento que vai estourar, calculados pelo código (a IA só explica) |
| 🎯 **Metas e Orçamento** | Metas com prazo e limite mensal por categoria |
| 🖥️ **App Desktop (Windows)** | Janela nativa com instalador, chat com IA em streaming, ocultar valores e bloqueio por PIN |
| 💾 **Backup** | Cópia semanal automática e restauração em um clique |
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

## 🖥️ App Desktop (Windows)

A interface principal é um **app nativo para Windows**: uma janela pywebview com frontend HTML/JS sobre uma API local FastAPI, que reaproveita os mesmos agentes da CLI.

```bash
pip install -e ".[desktop]"
python -m desktop.app
```

- **Início:** saldo nas contas, quanto entrou e saiu, ritmo de gastos, insight do mês, recorrentes, metas e watchlist
- **Chat com a IA** em tela cheia ou num painel flutuante, com a resposta aparecendo enquanto é escrita
- **Privacidade:** botão para ocultar valores (`R$ ••••`), bloqueio por PIN, chave da IA no Gerenciador de Credenciais do Windows
- **Backup** semanal automático e restauração em Ajustes
- Instalador em português, sem pedir administrador

Detalhes de telas, segurança, build e API em [`desktop/README.md`](desktop/README.md).

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
         ┌────▼────┐ ┌────▼────┐ ┌────▼──────┐
         │   CLI   │ │  Web    │ │ Desktop   │
         │ (Click  │ │(Stream- │ │(pywebview │
         │ + Rich) │ │ lit)    │ │ + FastAPI)│
         └────┬────┘ └────┬────┘ └────┬──────┘
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
  │ Collectors │  │ LLM (multi-   │  │   Models      │
  │ B3 / NYSE  │  │ provider)     │  │  SQLAlchemy   │
  │ CSV/Excel/ │  │ Ollama local  │  │  2.0 ORM      │
  │   PDF      │  │ + nuvem opc.  │  │               │
  └────────────┘  └───────────────┘  └───────┬───────┘
                                             │
                                      ┌──────▼──────┐
                                      │   SQLite    │
                                      │  (WAL mode) │
                                      └─────────────┘
```

- **BaseAgent (ABC)** → [`FinancialAgent`](stonks_ai/agents/financial_agent.py) + [`PersonalFinanceAgent`](stonks_ai/agents/personal_finance_agent.py)
- **Coletores modulares** para B3, NYSE/Nasdaq, e importação financeira (CSV, Excel, PDF)
- **LLM multi-provider** (Ollama local, DeepSeek, OpenAI, compatíveis) com fallback para o local e base de conhecimento nos prompts
- **App desktop** com API local protegida por token por sessão, CSP e bloqueio opcional por PIN
- **SQLite + SQLAlchemy 2.0** com WAL mode para performance
- **Configuração centralizada** em [`data/config.yaml`](data/config.yaml)

---

## 📁 Estrutura do Projeto

```
stonks-ai/
├── desktop/                      # App desktop (ver desktop/README.md)
│   ├── app.py, api.py, lock.py   # Janela, API local, bloqueio por PIN
│   ├── routes/                   # finance, market, assistant, settings
│   └── frontend/                 # HTML + CSS + JS (sem etapa de build)
├── evals/                        # Avaliação dos modelos de IA locais
├── stonks_ai/                    # Código-fonte principal
│   ├── main.py                   # CLI (Click + Rich)
│   ├── config.py                 # Gerenciamento de configuração YAML
│   ├── database.py               # SQLite + SQLAlchemy 2.0 (WAL mode)
│   ├── credentials.py            # Chave da IA no cofre do sistema
│   ├── backup.py                 # Backup e restauração do banco
│   ├── knowledge/                # Base de conhecimento usada nos prompts
│   ├── agents/                   # Agentes de IA (padrão ABC)
│   │   ├── base_agent.py         # Classe abstrata base
│   │   ├── financial_agent.py    # Agente de análise financeira
│   │   └── personal_finance_agent.py  # Agente de finanças pessoais
│   ├── collectors/               # Coletores de dados
│   │   ├── stocks/               # B3, NYSE/Nasdaq, Fundamentus
│   │   └── finance/              # Importação CSV, Excel, PDF
│   ├── llm/                      # Providers de IA + prompts
│   │   ├── factory.py            # Escolhe o provider e monta o fallback
│   │   ├── ollama_provider.py, openai_compatible_provider.py, ...
│   │   └── prompts.py            # Templates de prompt versionados
│   ├── models/                   # Modelos ORM (SQLAlchemy)
│   │   ├── stock_history.py
│   │   ├── transaction.py
│   │   ├── category.py
│   │   ├── financial_goal.py
│   │   ├── watchlist.py
│   │   ├── alert.py
│   │   ├── account.py
│   │   └── user_preferences.py
│   └── utils/                    # Utilitários
│       ├── charts.py             # Gráficos ASCII (plotext)
│       ├── formatters.py         # Formatadores de moeda/data
│       ├── validators.py         # Validadores de ticker, valores
│       ├── finance_utils.py      # Cálculos financeiros
│       ├── recurrence.py         # Transações recorrentes
│       └── insights.py           # Insights do mês calculados pelo código
├── tests/                        # Suíte de testes (pytest)
│   ├── test_agents.py
│   ├── test_cli.py
│   ├── test_collectors.py
│   ├── test_config.py
│   ├── test_database.py
│   ├── test_llm.py
│   ├── test_validators.py
│   ├── test_desktop_features.py  # Recorrentes, backup, cofre da chave
│   ├── test_desktop_api.py       # Rotas novas da API desktop
│   └── test_rules_insights_lock.py  # Categorização, insights, PIN
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
| [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) | 0.110+ / 0.29+ | API local do app desktop |
| [pywebview](https://pywebview.flowrl.com/) | 5.0+ | Janela nativa (WebView2) |
| [PyInstaller](https://pyinstaller.org/) + Inno Setup | 6.0+ / 6 | Executável e instalador |
| [keyring](https://github.com/jaraco/keyring) | 24+ | Chave da IA no cofre do sistema |
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
| [`docs/adr.md`](docs/adr.md) | Architecture Decision Records (20 ADRs documentados) |
| [`desktop/README.md`](desktop/README.md) | App desktop: telas, segurança, build, instalador e API local |
| [`evals/README.md`](evals/README.md) | Como avaliar os modelos de IA locais |
| [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) | Matriz de erros com 34 códigos e soluções |

---

## 🧪 Testes

```bash
# Dependências de teste (uma vez)
pip install -e ".[dev,e2e]" fastapi uvicorn
python -m playwright install chromium   # ou use o Edge já instalado no Windows

# Executar todos os testes (inclui os ponta a ponta do app desktop, que clicam no app num navegador)
pytest

# Com relatório de cobertura
pytest --cov=stonks_ai --cov-report=term-missing

# Testes específicos por módulo
pytest tests/test_collectors.py -v
pytest tests/test_agents.py -v

# Modo verboso com output detalhado
pytest -v --tb=long
```

Os testes rodam a cada push no GitHub Actions (`.github/workflows/testes.yml`), no Windows. Sem Ollama no CI, as respostas da IA são simuladas.

---

## 🗺️ Roadmap

### ✅ Concluído (v0.1.0)
- [x] **Multi-Provider LLM** — Ollama (local) + DeepSeek + OpenAI + OpenAI-compatible com fallback automático
- [x] **App desktop** — Substituiu a interface web em Streamlit (removida)
- [x] **Finanças Pessoais** — Importação CSV/Excel/PDF, categorização, metas, alertas
- [x] **Watchlist e Comparação** — Gerenciamento de ativos e comparação lado a lado
- [x] **App Desktop** — Janela nativa para Windows com instalador (ADR 015)
- [x] **Orçamento Mensal** — Limites por categoria, com aviso quando o ritmo vai estourar
- [x] **Recorrentes, backup, PIN e cofre da chave** — ADRs 016 a 018
- [x] **Categorização que aprende** — Regras por estabelecimento a partir das correções (ADR 020)

### 🔜 Em Breve
- [ ] **Suporte a Criptomoedas** — Integração com CoinGecko e CoinMarketCap
- [ ] **Notificações em Tempo Real** — Alertas de preço alvo via desktop/email
- [ ] **IA para estabelecimentos novos** — Chamar o modelo local só quando não houver regra, com cache
- [ ] **Windows Hello** — Desbloquear o app com biometria no lugar do PIN

### 📋 Planejado
- [ ] **Interface TUI** — Modo texto interativo com [Textual](https://textual.textualize.io/)
- [ ] **Modo Servidor (API REST)** — Endpoint HTTP para integração com outros sistemas
- [ ] **Exportação de Relatórios** — Geração de relatórios em PDF e Excel
- [ ] **Multi-idioma** — Suporte a inglês e espanhol na interface
- [ ] **Plugins** — Sistema de extensões para coletores e análises personalizadas
- [ ] **Integração com Corretoras** — API para consulta de posições e geração de ordens
- [ ] **Carteira de Investimentos** — Portfolio tracker com rentabilidade

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

[Relatar Bug](https://github.com/stonks-ai/stonks-ai/issues) · [Solicitar Feature](https://github.com/stonks-ai/stonks-ai/issues) · [Discutir](https://github.com/stonks-ai/stonks-ai/discussions)

</div>

STONKS AI E UM PROJETO EM DESENVOLVIMENTO
