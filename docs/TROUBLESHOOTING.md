# 🔧 Troubleshooting — Matriz de Erros

## Matriz Completa de Erros (E001-E034)

### Coletores de Ações (E001-E010)

| Código | Erro | Causa | Solução |
|--------|------|-------|---------|
| **STK-001** | Ticker inválido | Ticker não existe na B3 | Verifique o ticker (ex: PETR4, VALE3, WEGE3) |
| **STK-002** | Formato inválido | Ticker não segue padrão BR (4 letras + número) | Use formato BR para B3 |
| **STK-003** | Falha de rede | Sem conexão com Yahoo Finance | Verifique internet |
| **STK-004** | Sem dados | Ticker válido sem dados disponíveis | Tente outro período |
| **STK-005** | Erro de parse | Resposta inesperada da API | Reporte o bug |
| **STK-006** | Ticker US na B3 | Ticker americano enviado para B3 | Use `-e NYSE` |
| **STK-007** | Ticker NYSE inválido | Ticker não encontrado na NYSE/Nasdaq | Verifique o ticker |
| **STK-008** | Ticker BR no NYSE | Ticker brasileiro enviado para NYSE | Remova `-e NYSE` para auto-detectar |
| **STK-009** | Sem fundamentals | Dados fundamentalistas indisponíveis | Pode não haver dados para este ativo |
| **STK-010** | Timeout | Yahoo Finance demorou a responder | Tente novamente ou use período menor |

### LLM / Ollama (E020-E025)

| Código | Erro | Causa | Solução |
|--------|------|-------|---------|
| **LLM-001** | Ollama não rodando | Serviço Ollama não iniciado | Execute `ollama serve` |
| **LLM-002** | Modelo não encontrado | Modelo não foi baixado | Execute `ollama pull llama3.2:3b` |
| **LLM-003** | GPU OOM | Memória GPU insuficiente | Use modelo menor: `ollama pull llama3.2:1b` |
| **LLM-004** | Resposta inválida | Modelo retornou formato inesperado | Tente novamente |
| **LLM-005** | Contexto excedido | Prompt muito longo | Reduza a quantidade de dados |
| **LLM-006** | Timeout | Modelo demorou a responder | Aumente `llm.timeout` no config |

### Database / Config (E026-E030)

| Código | Erro | Causa | Solução |
|--------|------|-------|---------|
| **DB-001** | DB não inicializado | `stonks init` não foi executado | Execute `stonks init` |
| **DB-002** | Migração | Schema desatualizado | Execute `stonks init` para recriar |
| **DB-003** | Disco/IO | Problema de permissão ou disco cheio | Verifique espaço e permissões |
| **CFG-001** | YAML inválido | config.yaml corrompido | Delete e execute `stonks init` |
| **CFG-002** | Config ausente | Primeira execução | Execute `stonks init` |

### CLI / UX (E031-E034)

| Código | Erro | Causa | Solução |
|--------|------|-------|---------|
| **CLI-001** | Comando inválido | Comando não reconhecido | Use `stonks --help` |
| **CLI-002** | Argumento faltando | Parâmetro obrigatório não informado | Verifique a sintaxe do comando |
| **CLI-003** | Exchange inválida | Use apenas B3 ou NYSE | Use `-e B3` ou `-e NYSE` |
| **CLI-004** | Erro interno | Bug inesperado | Reporte com log do erro |

---

## ❓ FAQ

### "Ollama" é obrigatório?
Não. Análises com IA são opcionais. Você pode usar todos os comandos de cotação e histórico sem Ollama.

### Como trocar o modelo LLM?
```bash
stonks config --set llm.model llama3.2:1b
```

### O banco de dados enche?
O SQLite armazena histórico de consultas. Você pode limpar manualmente excluindo o arquivo `~/.stonks_ai/data/stonks_ai.db`.

---

## 📞 Suporte

- Abra uma [issue no GitHub](https://github.com/seu-usuario/stonks-ai/issues)
- Inclua o log de erro completo
- Informe versão do Python, SO e comando utilizado
