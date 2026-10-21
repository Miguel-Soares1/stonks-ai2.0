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
| **LLM-002** | Modelo não encontrado | Modelo não foi baixado | Execute `ollama pull qwen2.5:3b` |
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
O SQLite armazena histórico de consultas. Você pode limpar manualmente excluindo o arquivo `stonks_ai.db` da pasta de dados. **Faça um backup antes** (Ajustes → Backup).

### Esqueci o PIN do app desktop
O PIN protege o app aberto, mas não criptografa os dados, então nada se perde:
1. Feche o app.
2. Abra o `config.yaml` da pasta de dados (`%APPDATA%\StonksAI` no app instalado).
3. Apague o valor de `pin_hash` (deixe `pin_hash: ''`) e salve.
4. Abra o app e defina um PIN novo em Ajustes, se quiser.

### "Muitas tentativas. Aguarde N s."
Depois de 3 PINs errados seguidos, cada erro novo aumenta a espera (5 s, 10 s, 20 s... até 5 minutos). Espere o tempo indicado e digite o PIN certo.

### Restaurei um backup errado
Antes de cada restauração, o app salva uma cópia de como os dados estavam, com o tipo **"Antes de restaurar"** na lista de Ajustes → Backup. Restaure essa cópia para voltar.

### A opção de IA na nuvem sumiu dos Ajustes
Foi removida: o app usa só a IA local (Ollama), que é gratuita e não manda seus dados para fora (ADR 025). Se você tinha uma chave do DeepSeek ou da OpenAI salva por uma versão antiga, ela pode ter ficado no Gerenciador de Credenciais do Windows (entrada `StonksAI`); apague por lá se quiser.

### Uma transação sempre cai na categoria errada
Edite a transação e escolha a categoria certa. O app aprende o estabelecimento, corrige as transações iguais e acerta nas próximas importações. Para desfazer uma regra, vá em Orçamento → Regras aprendidas.

### Uma transação recorrente não apareceu
As ocorrências são criadas quando a data chega, ao abrir o app ou ao carregar o Início. Se você excluiu uma ocorrência, ela não é recriada. Para parar a série, edite qualquer transação dela e escolha "Não repete".

---

## 📞 Suporte

- Abra uma [issue no GitHub](https://github.com/seu-usuario/stonks-ai/issues)
- Inclua o log de erro completo
- Informe versão do Python, SO e comando utilizado
