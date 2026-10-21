# Configuração

## 📁 Localização do Arquivo

O `config.yaml` é criado automaticamente (pelo `stonks init` ou ao abrir o app desktop) na pasta de dados:

| Modo | Pasta |
|------|-------|
| Desenvolvimento (rodando do código) | `data/` do projeto |
| App desktop instalado | `%APPDATA%\StonksAI` |
| Qualquer modo | o que estiver em `STONKS_DATA_DIR`, se definido |

Na mesma pasta ficam o banco (`stonks_ai.db`) e os backups (`backups/`).

---

## 📄 Estrutura Completa

```yaml
database:
  path: ~/.stonks_ai/data/stonks_ai.db   # Caminho do banco SQLite

llm:
  model: qwen2.5:3b                      # Modelo Ollama
  endpoint: http://localhost:11434        # Endpoint do Ollama
  temperature: 0.3                        # Temperatura (0.0 - 1.0)
  max_tokens: 2048                        # Máximo de tokens por resposta
  timeout: 30                             # Timeout em segundos

finance:
  alert_interval_hours: 24                # Intervalo entre verificações de alerta
  dashboard_days_history: 90              # Dias de histórico no dashboard
  default_currency: BRL                   # Moeda padrão
  import_default_source: manual           # Origem padrão de importação

ui:
  language: pt-BR                         # Idioma (pt-BR, en-US)
  theme: dark                             # Tema (dark, light)
```

---

## ⚙️ Opções Detalhadas

### Database

| Chave | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `database.path` | string | `~/.stonks_ai/data/stonks_ai.db` | Caminho do arquivo SQLite |

### LLM (Ollama)

| Chave | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `llm.model` | string | `qwen2.5:3b` | Modelo Ollama para análises |
| `llm.endpoint` | string | `http://localhost:11434` | URL do servidor Ollama |
| `llm.temperature` | float | `0.3` | Criatividade das respostas (0.0 =保守, 1.0 = criativo) |
| `llm.max_tokens` | int | `2048` | Limite de tokens por resposta |
| `llm.timeout` | int | `30` | Timeout em segundos |

### Modelos Ollama Recomendados

Medido com `python -m evals.tools_eval` e `python -m evals.run_eval` (outubro de 2026). Modelos sem suporte a ferramentas (como o `gemma3`) funcionam, mas sem consultar cotações e os seus dados.

| Modelo | Tamanho | RAM Necessária | Qualidade |
|--------|---------|----------------|-----------|
| `qwen2.5:3b` | ~2GB | 4GB | ⭐ Recomendado: o melhor nas ferramentas do chat (93%) e nas perguntas de conceito |
| `llama3.2:3b` | ~2GB | 4GB | ✅ Bom no texto, mas usa ferramenta em pergunta de conceito (80%) e ocupa mais memória |
| `llama3.2:1b` | ~1,3GB | 2GB | ✅ Rápido, básico (74% nas ferramentas) |
| `mistral:7b` | ~4.1GB | 8GB | ⭐ Excelente |
| `gemma2:2b` | ~1.6GB | 4GB | ✅ Bom |

### UI

| Chave | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `ui.language` | string | `pt-BR` | Idioma da interface |
| `ui.theme` | string | `dark` | Tema visual |

### IA na nuvem (removida)

As opções `llm.provider`, `llm.api_key`, `llm.base_url` e `llm.fallback_provider` não existem mais: a IA
é sempre o Ollama local (ADR 025). Ao abrir, o app apaga essas chaves de um `config.yaml` antigo; quem
usava DeepSeek ou OpenAI volta para o modelo padrão do Ollama.

### UI e segurança do app desktop

| Chave | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `ui.theme` | string | `system` | `light`, `dark` ou `system` (segue o Windows) |
| `ui.hide_values` | bool | `false` | Ocultar valores (`R$ ••••`); muda pelo botão de olho no topo |
| `security.pin_hash` | string | `""` | Hash scrypt do PIN. Vazio = sem bloqueio. **Não edite à mão**, exceto para apagar se esquecer o PIN |
| `security.lock_after_minutes` | int | `10` | Bloquear de novo após N minutos sem uso: `0` (só ao abrir), `5`, `10`, `30` ou `60` |

### Finance (Finanças Pessoais)

| Chave | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `finance.alert_interval_hours` | int | `24` | Intervalo mínimo entre verificações de alerta (horas) |
| `finance.dashboard_days_history` | int | `90` | Dias de histórico exibidos no dashboard |
| `finance.default_currency` | string | `BRL` | Moeda padrão para transações |
| `finance.import_default_source` | string | `manual` | Origem padrão para importação |

---

## 🔧 Gerenciando via CLI

```bash
# Ver configuração atual
stonks config --show

# Alterar modelo LLM
stonks config --set llm.model mistral:7b

# Alterar temperatura
stonks config --set llm.temperature 0.5

# Alterar idioma
stonks config --set ui.language en-US
```

---

## 📝 Edição Manual

Você pode editar o arquivo `config.yaml` diretamente com qualquer editor de texto:

```bash
# Linux/macOS
nano ~/.stonks_ai/config.yaml

# Windows (PowerShell)
notepad $env:USERPROFILE\.stonks_ai\config.yaml
```

Após editar, as alterações são aplicadas automaticamente na próxima execução.
