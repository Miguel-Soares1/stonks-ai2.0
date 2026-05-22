# Configuração

## 📁 Localização do Arquivo

O `config.yaml` é criado automaticamente ao executar `stonks init` em:

| Sistema | Caminho |
|---------|---------|
| Windows | `C:\Users\SEU_USUARIO\.stonks_ai\config.yaml` |
| Linux | `~/.stonks_ai/config.yaml` |
| macOS | `~/.stonks_ai/config.yaml` |

---

## 📄 Estrutura Completa

```yaml
database:
  path: ~/.stonks_ai/data/stonks_ai.db   # Caminho do banco SQLite

llm:
  model: llama3.2:3b                      # Modelo Ollama
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
| `llm.model` | string | `llama3.2:3b` | Modelo Ollama para análises |
| `llm.endpoint` | string | `http://localhost:11434` | URL do servidor Ollama |
| `llm.temperature` | float | `0.3` | Criatividade das respostas (0.0 =保守, 1.0 = criativo) |
| `llm.max_tokens` | int | `2048` | Limite de tokens por resposta |
| `llm.timeout` | int | `30` | Timeout em segundos |

### Modelos Ollama Recomendados

| Modelo | Tamanho | RAM Necessária | Qualidade |
|--------|---------|----------------|-----------|
| `llama3.2:3b` | ~2GB | 4GB | ⭐ Recomendado |
| `llama3.2:1b` | ~0.6GB | 2GB | ✅ Rápido, básico |
| `mistral:7b` | ~4.1GB | 8GB | ⭐ Excelente |
| `gemma2:2b` | ~1.6GB | 4GB | ✅ Bom |

### UI

| Chave | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `ui.language` | string | `pt-BR` | Idioma da interface |
| `ui.theme` | string | `dark` | Tema visual |

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
