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
| 💼 **Carteira de Investimentos** | Importa os extratos da B3 (Negociação e Movimentação); preço médio, resultado, proventos, rentabilidade contra CDI e Ibovespa e patrimônio total no Início |
| 💰 **Finanças Pessoais** | Importe extratos de CSV, Excel e PDF; categorização automática que **aprende quando você corrige** |
| 🔁 **Transações Recorrentes** | Aluguel, salário e assinaturas lançados sozinhos quando a data chega |
| 💡 **Insights do Mês** | Categoria que mais subiu e orçamento que vai estourar, calculados pelo código (a IA só explica) |
| 🎯 **Metas e Orçamento** | Metas com prazo e limite mensal por categoria |
| 🖥️ **App Desktop (Windows)** | Janela nativa com instalador, chat com IA em streaming, ocultar valores e bloqueio por PIN |
| 📤 **Exportação para Excel** | Transações do ano e relatório da carteira para o Imposto de Renda (bens e direitos, proventos, vendas) |
| 💾 **Backup** | Cópia semanal automática e restauração em um clique |
| 📁 **Histórico Persistente** | Todas as consultas salvas em banco SQLite local |
| 🛡️ **Tratamento Estruturado de Erros** | Matriz de erros com 34 códigos e soluções documentadas |

---

## 🚀 Quick Start

```bash
# 1. Instalar
pip install stonks-ai

# 2. Baixar modelo LLM (opcional, para análise com IA)
ollama pull qwen2.5:3b

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

- **Carteira:** importação dos extratos da B3, preço médio pelo método da Receita, resultado, proventos e rentabilidade contra CDI e Ibovespa
- **Início:** saldo nas contas, quanto entrou e saiu, investimentos, ritmo de gastos, insight do mês, recorrentes, metas e watchlist
- **Chat com a IA** em tela cheia ou num painel flutuante, com a resposta aparecendo enquanto é escrita. A IA consulta o próprio app: "quanto está a PETR4?", "quanto gastei com iFood este mês?", "como está minha meta?" (ADR 026)
- **Privacidade:** botão para ocultar valores (`R$ ••••`), bloqueio por PIN; a IA roda só no seu computador
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
  model: qwen2.5:3b
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
  │ Collectors │  │ LLM local     │  │   Models      │
  │ B3 / NYSE  │  │ (Ollama)      │  │  SQLAlchemy   │
  │ CSV/Excel/ │  │               │  │  2.0 ORM      │
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
- **IA só local** (Ollama), gratuita e sem enviar dados para fora, com base de conhecimento nos prompts (ADR 025)
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
│   ├── backup.py                 # Backup e restauração do banco
│   ├── knowledge/                # Base de conhecimento usada nos prompts
│   ├── agents/                   # Agentes de IA (padrão ABC)
│   │   ├── base_agent.py         # Classe abstrata base
│   │   ├── financial_agent.py    # Agente de análise financeira
│   │   └── personal_finance_agent.py  # Agente de finanças pessoais
│   ├── collectors/               # Coletores de dados
│   │   ├── stocks/               # B3, NYSE/Nasdaq, Fundamentus
│   │   └── finance/              # Importação CSV, Excel, PDF
│   ├── llm/                      # IA local (Ollama) + prompts
│   │   ├── factory.py            # Cria o cliente do Ollama com o config.yaml
│   │   ├── ollama_provider.py
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
│   ├── test_desktop_features.py  # Recorrentes, backup, IA só local, logo
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
| [`docs/adr.md`](docs/adr.md) | Architecture Decision Records (23 ADRs documentados) |
| [`docs/CARTEIRA.md`](docs/CARTEIRA.md) | Como a carteira calcula: preço médio, importação da B3 e rentabilidade |
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

### ✅ Concluído (até v0.2.0)
- [x] **App desktop** — Substituiu a interface web em Streamlit (removida)
- [x] **Finanças Pessoais** — Importação CSV/Excel/PDF, categorização, metas, alertas
- [x] **Watchlist e Comparação** — Gerenciamento de ativos e comparação lado a lado
- [x] **App Desktop** — Janela nativa para Windows com instalador (ADR 015)
- [x] **Orçamento Mensal** — Limites por categoria, com aviso quando o ritmo vai estourar
- [x] **Recorrentes, backup e PIN** — ADRs 016 a 018
- [x] **Categorização que aprende** — Regras por estabelecimento a partir das correções (ADR 020)
- [x] **IA para estabelecimentos novos** — "Organizar com IA" chama o modelo local uma vez por estabelecimento em "Outros" (ADR 020)
- [x] **Testes ponta a ponta e CI** — Playwright clicando no app; GitHub Actions no Windows a cada push
- [x] **Carteira de Investimentos** — Importação dos extratos de Negociação e Movimentação da B3, preço médio, resultado, proventos e patrimônio total no Início (ADR 021)
- [x] **Exportação para Excel** — Transações do ano (resumo por mês e despesas por categoria) e relatório da carteira para o IR (ADR 023)
- [x] **Rentabilidade contra CDI e Ibovespa** — Retorno ponderado no tempo, dia a dia, e "% do CDI" (ADR 022; contas explicadas em [`docs/CARTEIRA.md`](docs/CARTEIRA.md))

- [x] **Alertas de preço-alvo no desktop** — Notificação do Windows com o app na bandeja; abrir com o Windows (sem e-mail: exigiria guardar senha de SMTP)
- [x] **Criptomoedas na carteira** — BTC, ETH e outras 17, em reais (par em dólar × câmbio), na rentabilidade e no relatório do IR (ADR 024)
- [x] **IA só local** — IAs na nuvem (DeepSeek, OpenAI) removidas: gratuito e nada sai do computador (ADR 025)
- [x] **IA que consulta o app** — Cotações, indicadores, gastos, contas, carteira, metas, orçamento, watchlist e calculadora no chat; modelo padrão `qwen2.5:3b`, escolhido por medição (ADR 026)

### 🔜 Próximos
1. [ ] **IA que lança no app, com confirmação** — "anota um gasto de R$ 50 no mercado", "aporta R$ 200 na meta da viagem", "põe a WEGE3 na watchlist": a IA prepara a ação e a tela mostra um botão para confirmar antes de gravar. Hoje as ferramentas do chat só leem (ADR 026)

### 📋 Depois
- [ ] **Relatórios em PDF** — Se o Excel não bastar
- [ ] **Criptografar o banco** — Protege os dados de verdade; o PIN só protege a tela
- [ ] **Windows Hello** — Biometria no lugar do PIN

### 🚫 Descartados (por enquanto)
O projeto é **gratuito e sem custo para manter**: nada que dependa de pagamento entra no roadmap.

| Ideia | Por quê |
|---|---|
| IAs na nuvem (DeepSeek, OpenAI) | Cobram por uso e mandam os dados para fora. Removidas em 21/10/2026 (ADR 025); o esforço vai para a IA local |
| Assinar o executável e o instalador | Exige um certificado de assinatura de código, que é pago. Sem ele, o Windows mostra o aviso do SmartScreen na primeira instalação ("Mais informações" → "Executar assim mesmo") |
| Interface TUI (Textual) | Seria a terceira interface; a CLI já cobre o modo texto e o Streamlit foi removido para ter uma só |
| Modo servidor (API REST aberto) | A API existe, mas presa ao `127.0.0.1` e com token de propósito; abrir para a rede contraria o modelo de segurança |
| Multi-idioma | O produto é brasileiro (B3, Pix, CDI, IR, bancos locais) |
| Plugins | Ninguém para escrevê-los, e seria código de terceiros com acesso às finanças |
| Integração com corretoras / ordens | Sem API para pessoa física no Brasil; ordens a partir de um modelo pequeno que erra é risco demais. A importação da B3 cobre a consulta de posições |

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
