# 📋 Stonks AI — Architecture Decision Records (ADR)

> **Propósito:** Registrar decisões arquiteturais importantes, incluindo contexto, alternativas consideradas e rationale.
> **Formato:** Baseado no template de Michael Nygard (http://thinkrelevance.com/blog/2011/11/15/documenting-architecture-decisions)

---

## ADR 001: Uso de LLM Local via Ollama

**Status:** ✅ Aceito  
**Data:** 2026  
**Tipo:** 🏗️ Fundação

### Contexto
Precisávamos de um modelo de linguagem para análise de ações e chat financeiro. As opções incluíam APIs cloud (OpenAI, Anthropic) ou execução local.

### Decisão
Optamos por **Ollama** com modelo padrão `llama3.2:3b`, executando localmente.

### Alternativas Consideradas
| Alternativa | Prós | Contras |
|---|---|---|
| **OpenAI API** | Modelo mais poderoso, resposta rápida | Custo por token, dependência de internet, dados enviados para nuvem |
| **Anthropic Claude** | Similar à OpenAI | Mesmos problemas da OpenAI |
| **Hugging Face Transformers** | Mais controle, open-source | Mais complexo de configurar, maior footprint |
| **Ollama** | Simples de configurar, roda local, muitos modelos disponíveis | Performance dependente de hardware, modelos menores que GPT-4 |

### Consequências
- ✅ Privacidade total — dados nunca saem da máquina
- ✅ Zero custo operacional (exceto eletricidade)
- ✅ Fácil troca de modelo (`config.yaml`)
- ❌ Análises mais lentas em hardware modesto
- ❌ Qualidade da análise limitada ao modelo escolhido

---

## ADR 002: SQLite como Banco de Dados

**Status:** ✅ Aceito  
**Data:** 2026  
**Tipo:** 🏗️ Fundação

### Contexto
O projeto precisava de persistência para watchlist, histórico, transações financeiras e metas.

### Decisão
Optamos por **SQLite** com SQLAlchemy 2.0 e WAL mode.

### Alternativas Consideradas
| Alternativa | Prós | Contras |
|---|---|---|
| **PostgreSQL** | Robusto, concorrência, recursos avançados | Setup complexo, servidor separado, overhead |
| **SQLite** | Zero configuração, arquivo único, embutido, rápido para dados locais | Sem concorrência real, sem autenticação, limitações de tamanho |
| **JSON file** | Simples de implementar | Sem queries, sem integridade, sem relacionamentos |
| **DuckDB** | Analytics-friendly, colunar | Ecossistema menor, menos maturidade |

### Consequências
- ✅ Zero configuração — `stonks init` cria o banco automaticamente
- ✅ Portabilidade — banco é um único arquivo; backup é copiar o arquivo
- ✅ WAL mode permite leitura durante escrita
- ❌ Não adequado para multi-usuário concorrente
- ❌ Limite prático de ~100GB (não será um problema para uso pessoal)

---

## ADR 003: Click + Rich para CLI

**Status:** ✅ Aceito  
**Data:** 2026  
**Tipo:** 🏗️ Fundação

### Contexto
Precisávamos de uma interface de linha de comando robusta e visualmente atraente.

### Decisão
Optamos por **Click** para definição de comandos e **Rich** para saída formatada.

### Alternativas Consideradas
| Alternativa | Prós | Contras |
|---|---|---|
| **argparse** | Nativo do Python | Verboso, sem subcomandos elegantes, saída sem cor |
| **Click** | Decoradores, subcomandos, tipagem, autocomplete | Dependência externa |
| **Typer** | Moderno, tipado, async | Menos maturidade que Click |
| **Rich** | Tabelas, cores, markdown, gráficos ASCII | Dependência externa |
| **Textual** | TUI interativa | Complexidade extra, overkill inicial |

### Consequências
- ✅ CLI profissional com tabelas, cores, gráficos e spinners de carregamento
- ✅ Comandos tipados com validação automática
- ✅ Fácil adicionar novos comandos via decoradores
- ❌ Maior dependência externa (mas bibliotecas maduras e estáveis)

---

## ADR 004: yfinance como Fonte de Dados de Ações

**Status:** ✅ Aceito  
**Data:** 2026  
**Tipo:** 🏗️ Fundação

### Contexto
Precisávamos de uma fonte de dados para cotações, histórico e indicadores fundamentalistas de ações B3 e NYSE.

### Decisão
Optamos por **yfinance** (biblioteca Python que consome Yahoo Finance).

### Alternativas Consideradas
| Alternativa | Prós | Contras |
|---|---|---|
| **yfinance** | Gratuito, cobre B3 e NYSE, dados fundamentalistas | Não oficial, pode quebrar se Yahoo mudar API |
| **B3 API oficial** | Dados oficiais | Precisa de cadastro, limites de requisição, complexa |
| **Alpha Vantage** | API gratuita com limites generosos | Precisa de API key, limites por minuto |
| **Investing.com scraping** | Dados detalhados | Frágil, anti-scraping, manutenção constante |
| **Brapi.dev** | API brasileira focada em B3 | Serviço terceiro, limites, pode ficar indisponível |

### Consequências
- ✅ Dados gratuitos e sem necessidade de cadastro
- ✅ Cobertura global (B3 + NYSE na mesma lib)
- ✅ Dados fundamentalistas inclusos
- ❌ Risco de quebra se Yahoo Finance alterar API (documentado em [`licoes.md`](../licoes.md))
- ❌ Latência variável dependendo do servidor Yahoo

---

## ADR 005: Separação em Agentes

**Status:** ✅ Aceito  
**Data:** 2026  
**Tipo:** 🏗️ Design

### Contexto
A lógica de negócio precisava de uma estrutura que separasse análise financeira de finanças pessoais, mas compartilhasse funcionalidades comuns (LLM, banco).

### Decisão
Criamos uma hierarquia com `BaseAgent` (ABC) e especializações `FinancialAgent` e `PersonalFinanceAgent`.

### Alternativas Consideradas
| Alternativa | Prós | Contras |
|---|---|---|
| **Agentes separados sem base** | Simples inicialmente | Duplicação de código |
| **BaseAgent abstrata** | Reuso, polimorfismo, extensível | Complexidade inicial maior |
| **Serviço único monolítico** | Mais simples | Viola SRP, difícil de estender |
| **Micro-serviços** | Maior separação | Overhead absurdo para projeto local |

### Consequências
- ✅ Fácil adicionar novos agentes (estender `BaseAgent`)
- ✅ LLM e banco compartilhados via herança
- ✅ `execute()` e `save_to_history()` padronizados
- ❌ Acoplamento à classe base (mudanças afetam todos agentes)

---

## ADR 006: Remoção do Módulo de Vagas (Jobs)

**Status:** ✅ Aceito — **Implementado**  
**Data:** 2026
**Tipo:** 🗑️ Remoção

### Contexto
O módulo de vagas (LinkedIn, Indeed, Workana, Upwork) foi uma das primeiras funcionalidades implementadas. Com o tempo, os scrapers quebravam constantemente devido a mudanças nas páginas dos sites, exigindo manutenção frequente.

### Decisão
Removemos **todo o módulo de vagas** do código, incluindo agentes, coletores, modelos ORM e comandos CLI.

### Alternativas Consideradas
| Alternativa | Prós | Contras |
|---|---|---|
| **Manter e corrigir** | Funcionalidade disponível | Manutenção constante e frustrante |
| **Usar APIs oficiais** | Dados estáveis | APIs pagas e/ou com limites restritivos |
| **Remover completamente** | Reduz superfície de manutenção | Perde funcionalidade |
| **Manter mas desabilitar** | Código preservado | Dead code, confusão |

### Consequências
- ✅ Redução significativa na manutenção necessária
- ✅ Código mais enxuto
- ❌ 8 erros descobertos pós-remoção (documentados em [`licoes.md`](../licoes.md))
- ❌ Banner do CLI ainda exibe "Vagas" (bug conhecido a ser corrigido)
- ❌ Testes precisaram ser adaptados

### Lições Aprendidas
1. Scrapers são frágeis e devem ser evitados em funcionalidades principais
2. Remoção de módulos grandes requer verificação cuidadosa de imports em todo o código
3. Testes que dependem de módulos removidos precisam ser identificados previamente
4. Documentar erros encontrados ajuda a evitar repetição

---

## ADR 007: Adição do Módulo de Finanças Pessoais

**Status:** ✅ Aceito — **Implementado**  
**Data:** 2026
**Tipo:** 🆕 Adição

### Contexto
Após a remoção do módulo de vagas, o projeto precisava de uma direção mais alinhada com o propósito principal: finanças. Finanças pessoais é um complemento natural à análise de ações.

### Decisão
Adicionamos um módulo completo de finanças pessoais com 6 componentes:
1. Modelos de dados (Category, Transaction, FinancialGoal, Alert)
2. Categorizador automático por regras
3. Importadores de extrato (CSV, Excel, PDF)
4. Dashboard financeiro
5. Metas financeiras com análise de IA
6. Alertas inteligentes

### Alternativas Consideradas
| Alternativa | Prós | Contras |
|---|---|---|
| **Módulo financeiro completo** | Alinhado com o propósito do projeto | Grande esforço de implementação |
| **Integração com APIs bancárias** | Dados reais automáticos | Complexidade, segurança, APIs fechadas |
| **Apenas importação manual** | Simples de implementar | Pouco valor para o usuário |
| **Usar biblioteca externa** | Menos código próprio | Dependência, falta de controle |

### Consequências
- ✅ Módulo coeso que complementa análise de ações
- ✅ Privacidade — extratos bancários processados localmente
- ✅ IA agrega valor real com análise de gastos e projeção de metas
- ❌ Grande aumento de código (~700+ linhas só no agente)
- ❌ Importação de PDF é frágil (formatos variam por banco)

---

## ADR 008: Interface Web com Streamlit

**Status:** ✅ Aceito  
**Data:** 2026
**Tipo:** 🏗️ Expansão

### Contexto
O CLI é poderoso, mas muitos usuários preferem interfaces gráficas. Precisávamos de uma UI web com baixo custo de desenvolvimento.

### Decisão
Optamos por **Streamlit** para a interface web, com **Plotly** para gráficos interativos.

### Alternativas Consideradas
| Alternativa | Prós | Contras |
|---|---|---|
| **Streamlit** | Rápido de prototipar, Python puro, estado gerenciado | Menos flexível que frameworks tradicionais |
| **Flask + Jinja** | Controle total | Muito mais código para o mesmo resultado |
| **FastAPI + React** | Moderno, performático | Stack JS separada, complexidade |
| **Gradio** | Focado em ML/IA | Menos flexível para UI geral |

### Consequências
- ✅ Mesmo código Python para CLI e Web
- ✅ Prototipagem rápida — app funcional em horas
- ✅ Gráficos interativos com Plotly
- ❌ Streamlit recarrega tudo a cada interação (não é SPA)
- ❌ Apenas um usuário por vez (arquitetura stateful)
- ❌ Webapp engessado para customizações visuais avançadas

---

## ADR 009: Uso de Códigos de Erro Estruturados

**Status:** ✅ Aceito  
**Data:** 2026
**Tipo:** 🏗️ Processo

### Contexto
Com a remoção do módulo de vagas, descobrimos múltiplos erros que não tinham sido antecipados. Precisávamos de um sistema para rastrear e documentar erros.

### Decisão
Adotamos um sistema de **códigos de erro** no formato `E-NNN` e `DB-NNN`, com documentação em [`licoes.md`](../licoes.md).

### Alternativas Consideradas
| Alternativa | Prós | Contras |
|---|---|---|
| **Códigos de erro** | Rastreável, buscável, documentado | Overhead inicial |
| **Apenas logs** | Simples | Difícil de rastrear |
| **Exception classes** | Tipado, catch preciso | Mais código |
| **Sentry/APM** | Automático, monitoramento | Dependência externa |

### Consequências
- ✅ Erros facilmente rastreáveis e referenciáveis
- ✅ Base de conhecimento crescente
- ✅ Útil tanto para humanos quanto para IAs lerem
- ❌ Requer disciplina para manter atualizado

---

## ADR 010: Python Puro sem Type Hints Rigorosos

**Status:** ✅ Aceito  
**Data:** 2026  
**Tipo:** 🏗️ Fundação

### Contexto
Precisávamos definir o nível de tipagem no código Python.

### Decisão
Usamos **type hints** Python modernos (`Optional`, `List`, `Dict`, `Any`) mas não adotamos verificadores estritos como `mypy --strict`.

### Alternativas Consideradas
| Alternativa | Prós | Contras |
|---|---|---|
| **Type hints completos** | Documentação, IDE, mypy strict | Mais código, mais tempo |
| **Sem type hints** | Mais rápido de escrever | Menos documentado, IDE menos útil |
| **Pydantic/DataClasses** | Validação automática | Dependência extra, mais código |
| **Type hints moderados (atual)** | Equilíbrio entre clareza e agilidade | Proteção parcial |

### Consequências
- ✅ Código legível com hints nos pontos críticos
- ✅ IDEs conseguem autocomplete e detecção de erros básicos
- ❌ Não pegamos todos os erros de tipo em tempo de compilação
- ❌ Algumas funções têm `Any` que poderiam ser mais específicas

---

## ADR 011: WebApp Monolítico em um Único Arquivo

**Status:** ⚠️ Aceito (com ressalvas)  
**Data:** 2026
**Tipo:** 🏗️ Design

### Contexto
A interface web foi adicionada quando o projeto já tinha uma base CLI consolidada. Precisávamos de uma UI funcional rapidamente.

### Decisão
Todo o código Streamlit foi colocado em **um único arquivo** [`webapp/app.py`](../webapp/app.py) (~1900 linhas).

### Alternativas Consideradas
| Alternativa | Prós | Contras |
|---|---|---|
| **Arquivo único** | Simples, rápido, sem preocupações com estrutura | Código monolítico, difícil de navegar |
| **Múltiplos módulos** | Organizado, testável, escalável | Mais arquivos, overhead de estrutura |
| **Pacote separado** | Separação clara entre CLI e Web | Complexidade de manutenção |

### Consequências
- ✅ Prototipagem e iteração muito rápidas
- ✅ Fácil de encontrar qualquer funcionalidade
- ❌ Arquivo com 1900+ linhas — difícil de manter
- ❌ Sem testes unitários para o webapp
- ❌ Refatoração em módulos menores é recomendada para o futuro

---

## ADR 012: Gerenciamento de Configuração via YAML

**Status:** ✅ Aceito  
**Data:** 2026  
**Tipo:** 🏗️ Fundação

### Contexto
O projeto precisava de configurações persistentes (modelo LLM, exchange padrão, preferências).

### Decisão
Optamos por **YAML** como formato de configuração, armazenado em [`data/config.yaml`](../data/config.yaml).

### Alternativas Consideradas
| Alternativa | Prós | Contras |
|---|---|---|
| **YAML** | Legível, suporta comentários, hierárquico | Sensível a indentação |
| **JSON** | Universal, parse nativo | Sem comentários, mais verboso |
| **TOML** | Simples, suportado pelo Python | Menos flexível para hierarquia |
| **.env** | Muito simples | Só chave=valor, sem estrutura |
| **Banco de dados** | Configuração dinâmica | Overhead para config simples |

### Consequências
- ✅ Configuração legível e editável manualmente
- ✅ Hierarquia natural para diferentes seções (LLM, stocks, finance)
- ✅ Fácil de versionar e comparar mudanças
- ❌ Erro de indentação pode quebrar a leitura

---

## Resumo de Decisões

| ADR | Decisão | Status | Impacto |
|---|---|---|---|
| 001 | LLM Local via Ollama | ✅ Aceito | Privacidade, zero custo, performance variável |
| 002 | SQLite + SQLAlchemy | ✅ Aceito | Zero config, portátil, sem concorrência |
| 003 | Click + Rich | ✅ Aceito | CLI profissional, dependências estáveis |
| 004 | yfinance | ✅ Aceito | Gratuito, global, risco de quebra |
| 005 | Agentes com BaseAgent ABC | ✅ Aceito | Reuso, extensibilidade, acoplamento |
| 006 | Remoção do módulo de vagas | ✅ Implementado | Menos manutenção, 8 erros pós-remoção |
| 007 | Adição de finanças pessoais | ✅ Implementado | Módulo coeso, grande aumento de código |
| 008 | Streamlit + Plotly | ✅ Aceito | Rápido, mesma linguagem, estado gerenciado |
| 009 | Códigos de erro estruturados | ✅ Aceito | Rastreável, buscável, documentado |
| 010 | Type hints moderados | ✅ Aceito | Equilíbrio clareza/agilidade |
| 011 | WebApp em arquivo único | ✅ Substituído | Refatorado em 12 módulos (ADR-013) |
| 012 | Config YAML | ✅ Aceito | Legível, hierárquico, versionável |
| 013 | Multi-Provider LLM + Fallback | ✅ Aceito | Ollama + DeepSeek + OpenAI, fallback chain |

---

## ADR 013: Arquitetura Multi-Provider LLM com Fallback Chain

**Status:** ✅ Aceito  
**Data:** 2026-06  
**Tipo:** 🏗️ Refatoração

### Contexto

O ADR-001 determinou o uso exclusivo de Ollama como provider LLM. Com o tempo, identificámos limitações:
1. A qualidade das análises fundamentalistas é limitada pelo modelo local (Llama 3.2 3B)
2. Utilizadores sem GPU adequada têm latência elevada
3. O sistema ficava completamente sem IA se o Ollama não estivesse disponível

### Decisão

Refatoramos o cliente LLM para uma arquitetura multi-provider com fallback chain:

1. **Interface abstrata** `BaseLLMProvider` com métodos `generate()`, `generate_from_messages()`, `generate_stream()`, `is_available()`
2. **Providers concretos:**
   - `OllamaProvider` — execução local (refactor do antigo `OllamaClient`)
   - `DeepSeekProvider` — API REST deepseek.com (~$0.14/1M tokens, melhor custo/benefício)
   - `OpenAIProvider` — API REST openai.com (GPT-4o-mini, GPT-4o)
   - `OpenAICompatibleProvider` — qualquer API OpenAI-compatible (OpenRouter, Groq, etc.)
3. **Factory** `create_llm_client(config)` que instancia o provider correto
4. **FallbackChain** — wrapper que tenta provider primário, cai no fallback (Ollama) se falhar
5. **Suporte a variáveis de ambiente** na config (`${ENV_VAR}`)

### Alternativas Consideradas

| Alternativa | Prós | Contras |
|---|---|---|
| **Manter só Ollama** | Simplicidade | Sem fallback, qualidade limitada |
| **Substituir Ollama por API** | Melhor qualidade | Perde privacidade, custo, offline |
| **Multi-provider (escolhido)** | Flexibilidade, fallback, privacidade | Complexidade adicional |

### Consequências

- ✅ Sistema nunca fica sem IA (fallback chain)
- ✅ Utilizador pode escolher entre privacidade (local) e qualidade (remoto)
- ✅ Finanças pessoais podem permanecer 100% locais
- ✅ Suporte a qualquer API OpenAI-compatible
- ✅ Streaming via SSE para providers remotos
- ❌ Mais código para manter (5 providers + factory + chain)
- ❌ API keys precisam de ser geridas com segurança

### Migração

```yaml
# Antes (apenas Ollama):
llm:
  model: llama3.2:3b
  endpoint: http://localhost:11434

# Depois (multi-provider):
llm:
  provider: deepseek          # ollama | deepseek | openai | openai_compatible
  model: deepseek-chat
  api_key: ${DEEPSEEK_API_KEY}
  fallback_provider: ollama   # fallback local se API falhar
```

### Configuração Recomendada

| Perfil | Provider | Custo mensal (est.) |
|---|---|---|
| Privacidade máxima | `ollama` | $0 |
| Melhor custo/benefício | `deepseek` | ~$1-2 |
| Melhor qualidade | `openai` (GPT-4o) | ~$5-10 |
| Flexível | `openai_compatible` | Variável |

---

## ADR 014: Refatoração do WebApp Monolítico

**Status:** ✅ Aceito  
**Data:** 2026-06  
**Tipo:** 🏗️ Refatoração

### Contexto

O ADR-011 registou a decisão de manter o webapp num único ficheiro (~2144 linhas) para prototipagem rápida. Com o crescimento do projeto, a manutenção tornou-se difícil e os testes impossíveis.

### Decisão

Refatoramos o `webapp/app.py` de 2144 linhas para 12 módulos (~90 linhas o router principal):

```
webapp/
├── app.py              # Router principal (~90 linhas)
├── theme.py            # Tema CSS escuro
├── components/         # Componentes reutilizáveis
│   ├── sidebar.py      # Barra lateral
│   ├── metrics.py      # Cards de métricas
│   └── charts.py       # Gráficos Plotly
└── pages/              # Páginas (1 ficheiro por página)
    ├── dashboard.py, chat.py, quote.py, history.py,
    ├── analyze.py, compare.py, watchlist.py,
    ├── finance.py, goals.py, alerts.py, config.py
```

### Consequências

- ✅ Cada página é isolada e testável
- ✅ Componentes reutilizáveis (sidebar, métricas, gráficos)
- ✅ Navegação mais rápida (menos código para o Streamlit processar)
- ✅ Fácil adicionar novas páginas
- ❌ Mais ficheiros para gerir (12 vs 1)

---

## ADR 015: App Desktop (pywebview + FastAPI) no lugar do Streamlit

**Status:** ✅ Aceito — todas as telas migradas para `desktop/`; o Streamlit (`webapp/`), a landing page e o dashboard público (`site/`) foram removidos em 20/10/2026: a landing descrevia um produto web/pago que não existe mais, e o app é local-first.
**Data:** 2026-10
**Tipo:** 🏗️ Refatoração

### Contexto
O ADR 008 já registrava os limites do Streamlit: recarrega a página inteira a cada interação, é difícil de personalizar visualmente e exige `streamlit run`. O objetivo agora é distribuir o Stonks AI como um executável para Windows, com uma interface própria.

### Decisão
Uma API local **FastAPI** sobre os agentes existentes, um frontend em **HTML/CSS/JS** sem etapa de build e uma janela nativa **pywebview** (WebView2), empacotados com **PyInstaller** (`--onedir`). No executável, os dados vão para `%APPDATA%\StonksAI`.

### Alternativas Consideradas
| Alternativa | Prós | Contras |
|---|---|---|
| **pywebview + FastAPI + HTML/JS** | Controle visual total, agentes reaproveitados sem mudança, API reutilizável (ex.: celular) | Duas linguagens (Python + JS) |
| **NiceGUI (native=True)** | Tudo em Python | Teto de design menor, preso aos componentes da biblioteca |
| **Flet** | Tudo em Python, visual moderno | Gráficos mais limitados, ecossistema menor |
| **Tauri / Electron + Python sidecar** | Instalador menor (Tauri) | Rust/Node na cadeia de build, mais complexidade |

### Consequências
- ✅ Visual e interação sem as amarras do Streamlit
- ✅ CLI e agentes continuam iguais; a API é só uma camada fina
- ✅ Dados do usuário fora da pasta do programa (instalável em Program Files)
- ❌ Executável grande (~260 MB, principalmente pandas, numpy e pymupdf)
- ❌ Executáveis PyInstaller podem gerar alertas de antivírus; requer instalador e, idealmente, assinatura
- ❌ A API local precisa de um token para não ficar acessível a outros processos da máquina

---

## ADR 016: Segredos e acesso local — chave da IA no cofre do sistema e bloqueio por PIN

**Status:** ✅ Aceito
**Data:** 2026-10
**Tipo:** 🔒 Segurança

### Contexto
A chave de uma IA na nuvem era salva em texto puro no `config.yaml` (Lição #5 de junho já apontava o risco). E o app desktop abria direto nas finanças: num computador compartilhado, qualquer pessoa via tudo.

### Decisão
- **Chave da IA:** vai para o cofre do sistema via `keyring` (Gerenciador de Credenciais no Windows). O `config.yaml` guarda só o marcador `@keyring`. Referências `${VARIAVEL}` continuam no config, porque não são segredo. Chaves antigas em texto puro são migradas ao abrir o app (`stonks_ai/credentials.py`). Sem cofre disponível (Linux sem serviço de chaves, Streamlit Cloud), volta a salvar no config.
- **PIN opcional:** hash scrypt com sal no config. Com PIN, o **middleware da API** responde `423` a qualquer rota de dados até o desbloqueio; só `/api/boot`, `/api/status` e `/api/lock/*` ficam livres. O desbloqueio vive só na memória (reabrir o app pede o PIN) e expira após um tempo sem uso (5 min a 1 h, ou só ao abrir). Erros seguidos aumentam a espera (5 s, 10 s, 20 s... até 5 min). Código em `desktop/lock.py`.

### Alternativas Consideradas
| Alternativa | Prós | Contras |
|---|---|---|
| **keyring + PIN na API** | Usa o cofre do SO; o bloqueio vale para qualquer cliente da API, não só para a tela | PIN não criptografa o banco |
| Criptografar o `config.yaml` | Tudo num arquivo | Onde guardar a chave de criptografia? Volta ao mesmo problema |
| Criptografar o banco (SQLCipher) | Protege os arquivos em disco | Dependência nativa no build; PIN esquecido = dados perdidos |
| Windows Hello | Biometria, sem PIN para lembrar | API do Windows via pywebview é complexa; fica para depois |
| Bloqueio só no frontend | Simples | Qualquer programa com o token leria a API |

### Consequências
- ✅ Nenhum segredo da IA em texto puro no disco
- ✅ O bloqueio é aplicado no servidor, não é só uma tela por cima
- ❌ O PIN protege o app aberto, não os arquivos: quem entra na conta do Windows lê a pasta de dados
- ❌ PIN esquecido exige apagar `security.pin_hash` no `config.yaml` com o app fechado (documentado no TROUBLESHOOTING)

---

## ADR 017: Backup pela API de backup do SQLite

**Status:** ✅ Aceito
**Data:** 2026-10
**Tipo:** 🗄️ Dados

### Contexto
Todos os dados ficam num único arquivo SQLite. Sem backup, um arquivo corrompido ou uma importação errada não tinham volta.

### Decisão
`stonks_ai/backup.py` usa `sqlite3.Connection.backup()`: copia o banco com segurança mesmo com o app aberto em modo WAL. As cópias ficam em `DATA_DIR/backups/stonks-AAAAMMDD-HHMMSS[-motivo].db`. Há um backup automático por semana (guarda os 8 últimos), backup manual e restauração da lista ou de um arquivo `.db` escolhido. Antes de restaurar, o app salva uma cópia do estado atual (`-antes`). O arquivo restaurado precisa passar no `PRAGMA integrity_check` e ter as tabelas do Stonks AI; nomes de backup são validados por regex (sem `../`).

### Alternativas Consideradas
| Alternativa | Prós | Contras |
|---|---|---|
| **API de backup do SQLite** | Consistente com WAL e app aberto; sem dependência | Cópia inteira a cada vez |
| Copiar o arquivo `.db` | Trivial | Pode copiar no meio de uma escrita; ignora o `-wal` |
| Exportar CSV/JSON | Legível | Restaurar exige reimportar e recriar relações |
| Sincronizar com a nuvem | Protege contra perder o PC | Dados saem da máquina (contra o ADR 001) |

### Consequências
- ✅ Dá para desfazer importações e restaurações
- ✅ O botão "Abrir pasta" facilita copiar os backups para um pendrive ou nuvem por conta própria
- ❌ Os backups ficam na mesma máquina; perder o computador perde os backups

---

## ADR 018: Transações recorrentes criadas quando a data chega

**Status:** ✅ Aceito
**Data:** 2026-10
**Tipo:** 💰 Finanças

### Contexto
O modelo `Transaction` já tinha `is_recurring`, `recurring_frequency` e `recurrence_id`, mas nenhuma tela os usava. Aluguel, salário e assinaturas precisavam ser lançados à mão todo mês.

### Decisão
Uma série é o grupo de transações com o mesmo `recurrence_id` (`stonks_ai/utils/recurrence.py`). A primeira define o dia de referência; a mais recente é o modelo das próximas (editar o valor da última vale daqui para frente). As ocorrências são **materializadas como transações normais quando a data chega** (ao abrir o app e ao carregar o Início), nunca adiantadas. A data da última ocorrência gerada fica em `user_preferences` (`recurrence_last:<id>`), para que uma ocorrência excluída não seja recriada. Recuperar o atraso tem teto de 60 ocorrências por série.

### Alternativas Consideradas
| Alternativa | Prós | Contras |
|---|---|---|
| **Materializar ao chegar a data** | Relatórios, orçamento e alertas funcionam sem mudança; dá para editar uma ocorrência | Precisa de um gatilho (abertura do app e Início) |
| Gerar o ano inteiro de uma vez | Simples | Polui o mês com lançamentos futuros; editar a série vira pesadelo |
| Calcular virtualmente nas consultas | Sem linhas extras no banco | Toda consulta (resumo, orçamento, alertas) teria que conhecer a regra |

### Consequências
- ✅ Nenhum código de relatório precisou mudar
- ✅ "Recorrentes no próximo mês" no Início (janela de 31 dias, para uma conta mensal sempre aparecer)
- ❌ Com o app fechado, as ocorrências só aparecem na próxima abertura

---

## ADR 019: Números do insight calculados pelo código; a IA só explica

**Status:** ✅ Aceito
**Data:** 2026-10
**Tipo:** 🤖 IA

### Contexto
O design do Figma Make propunha um card "Você pode economizar R$ 540" escrito pela IA. A avaliação (`evals/`) mede justamente os "números sem lastro" que os modelos locais pequenos inventam, e um número errado na tela inicial de um app financeiro destrói a confiança.

### Decisão
`stonks_ai/utils/insights.py` calcula os insights em Python: (1) a categoria com o maior aumento em reais, comparando **os mesmos N dias** do mês anterior quando o mês está em andamento; (2) a categoria que vai estourar o limite do orçamento no ritmo atual. Variações abaixo de R$ 50 ou 20% são ignoradas. O card mostra o número calculado; o botão "Entender com a IA" abre o chat com uma pergunta pronta que já contém esses números.

### Alternativas Consideradas
| Alternativa | Prós | Contras |
|---|---|---|
| **Código calcula, IA explica** | Número sempre correto; funciona sem IA | Menos "mágico" |
| IA gera o insight inteiro | Texto mais rico | Modelos de 1–3B inventam valores |
| IA gera e o código confere os números | Texto rico e verificado | Complexo; resposta lenta na tela inicial |

### Consequências
- ✅ O Início abre rápido e sem depender do Ollama
- ✅ Mesma regra vale para o futuro: números na tela vêm do banco, não do modelo
- ❌ Só dois tipos de insight por enquanto

---

## ADR 020: Categorização por regras aprendidas antes da IA

**Status:** ✅ Aceito
**Data:** 2026-10
**Tipo:** 💰 Finanças

### Contexto
A categorização tinha três problemas: palavras-chave casavam com pedaços de palavras ("DOC" pegava "DOCES"); o aprendizado por correção nunca era chamado pelo app e seu filtro descartava quase todas as palavras; e o importador tinha uma cópia separada da lógica. Além disso, `categorize_with_llm` existia mas **nenhum código a chamava**: a avaliação media a IA num caminho que o app não usa.

### Decisão
Um único `Categorizer` para importação, transação manual e edição, nesta ordem:
1. **Regra aprendida:** ao corrigir a categoria de uma transação, o estabelecimento (`merchant_key`: "COMPRA CARTAO PANVEL FARMACIAS LJ 33" vira "PANVEL FARMACIAS") passa a ir sempre para a categoria escolhida. Transações do mesmo estabelecimento que estavam na mesma categoria antiga são corrigidas junto. As regras ficam em `user_preferences` (`cat_rule:<estabelecimento>`) e podem ser apagadas em Orçamento.
2. **Palavra-chave como palavra inteira**, sem acento e aceitando plural, ganhando a mais específica ("AMAZON PRIME" vence "POSTO").
3. **"Outros".**

A IA continua fora da importação.

### Alternativas Consideradas
| Alternativa | Prós | Contras |
|---|---|---|
| **Regras aprendidas + palavras-chave** | Instantâneo, local, previsível, melhora com o uso | Primeira vez de um estabelecimento novo cai em "Outros" |
| IA para tudo que não casar | Acerta estabelecimentos novos | ~0,5 s por transação; extrato de 300 linhas trava a importação |
| Adicionar as palavras da descrição às palavras-chave (aprendizado antigo) | Já existia | Palavras genéricas ("PAGAMENTO") contaminam a categoria inteira |

### Consequências
- ✅ Corrigir uma vez resolve todas as transações daquele estabelecimento, inclusive nas próximas importações
- ✅ Cache compartilhado: uma regra aprendida vale na próxima importação sem reiniciar
- ❌ A IA ainda não ajuda com estabelecimentos novos. Próximo passo possível: chamar a IA só para estabelecimentos sem regra, com cache por estabelecimento

---

> Este documento deve ser atualizado sempre que uma nova decisão arquitetural for tomada.  
> Consulte também: [`MEMORY.md`](../MEMORY.md) | [`licoes.md`](../licoes.md)
