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
| 011 | WebApp em arquivo único | ⚠️ Aceito | Rápido, mas monolítico |
| 012 | Config YAML | ✅ Aceito | Legível, hierárquico, versionável |

---

> Este documento deve ser atualizado sempre que uma nova decisão arquitetural for tomada.  
> Consulte também: [`visao.md`](visao.md) | [`arquitetura.md`](arquitetura.md) | [`licoes.md`](../licoes.md)
