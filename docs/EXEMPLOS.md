# Exemplos Práticos

## 📊 Analisar PETR4 com IA

```bash
# 1. Cotação rápida
stonks quote PETR4

# 2. Histórico dos últimos 6 meses com gráfico
stonks history PETR4 --period 6mo --chart

# 3. Análise completa com IA (requer Ollama)
stonks analyze PETR4
```

**Saída esperada:**
- Cotação: Preço atual, variação, máx/mín do dia
- Histórico: Tabela com datas e preços + gráfico ASCII
- Análise: Resumo executivo, análise técnica, fundamentalista, riscos e recomendação

---

## ⚖️ Comparar VALE3 e BHP

```bash
# Comparar mineradoras brasileira e australiana
stonks compare VALE3 BHP
```

**Saída esperada:**
- Tabela lado a lado com preços, variação, P/L, DY
- Gráfico de performance relativa
- Recomendação ranqueada


## 👀 Configurar Watchlist com Acompanhamento

```bash
# Adicionar ativos
stonks watchlist --add PETR4 --name "Petrobras PN"
stonks watchlist --add AAPL -e NYSE --name "Apple Inc"
stonks watchlist --add VALE3 --name "Vale ON"
stonks watchlist --add WEGE3 --name "WEG"

# Listar watchlist
stonks watchlist

# Remover ativo
stonks watchlist --remove WEGE3
```

**Saída esperada:**
```
┌──────┬────────┬──────────┬────────────┬──────────┐
│ #    │ Ativo  │ Bolsa    │ Nome       │ Adicion. │
├──────┼────────┼──────────┼────────────┼──────────┤
│ 1    │ PETR4  │ B3       │ Petrobr... │ 12/03   │
│ 2    │ AAPL   │ NYSE     │ Apple Inc  │ 12/03   │
│ 3    │ VALE3  │ B3       │ Vale ON    │ 12/03   │
└──────┴────────┴──────────┴────────────┴──────────┘
```

---

## 📈 Relatório de Múltiplos Ativos

```bash
# Cotação de vários ativos simultâneos
stonks compare PETR4 VALE3 BBAS3 WEGE3 ITUB4

# Análise individual com IA
stonks analyze PETR4
stonks analyze VALE3
stonks analyze BBAS3
```

---

## 🆘 Quando a IA não está disponível

Sem Ollama, os comandos funcionam normalmente:

```bash
# Funciona sem IA
stonks quote PETR4
stonks history AAPL -e NYSE --chart

# Mostra apenas dados (sem análise IA)
stonks analyze VALE3
```

---

## 💰 Importar Extrato Bancário (CSV)

```bash
# Importar extrato do Nubank
stonks finance import extrato_nubank.csv
```

**Saída esperada:**
```
Importando extrato_nubank.csv...
45 transações importadas com sucesso!
2 duplicatas ignoradas
```

### Importar de outros formatos

```bash
# Excel
stonks finance import extrato_itau.xlsx

# PDF
stonks finance import fatura_cartao.pdf
```

**Detecção automática:** O sistema identifica o banco pelo nome do arquivo ou cabeçalhos (Nubank, Inter, C6 Bank, Itaú, Bradesco, Santander).

---

## 📋 Listar e Categorizar Transações

```bash
# Listar todas as transações
stonks finance transactions

# Filtrar apenas despesas dos últimos 30 dias
stonks finance transactions --type expense --days 30

# Filtrar por categoria
stonks finance transactions --category 1 --limit 20

# Ver categorias disponíveis
stonks finance categories
```

**Saída esperada:**
```
┌──────┬────────────┬──────────────────────┬──────────────┬──────────────┐
│ ID   │ Data       │ Descrição            │ Categoria    │ Valor        │
├──────┼────────────┼──────────────────────┼──────────────┼──────────────┤
│ 42   │ 15/01/2025 │ IFOOD - Hamburguer   │ Alimentação  │ - R$ 45,90   │
│ 43   │ 15/01/2025 │ NETFLIX ASSINATURA   │ Assinaturas  │ - R$ 55,90   │
│ 44   │ 14/01/2025 │ SALARIO              │ Salário      │ + R$ 5.000   │
└──────┴────────────┴──────────────────────┴──────────────┴──────────────┘
```

---

## ➕ Adicionar Transação Manualmente

```bash
# Adicionar receita
stonks finance add "Freelance Projeto X" 2500 --type income --date 2025-01-20

# Adicionar despesa (categorização automática)
stonks finance add "Ifood - Hamburguer" 45.90

# Adicionar com categoria específica
stonks finance add "Netflix" 55.90 --type expense --category Assinaturas

# Adicionar com observações
stonks finance add "Material Escritório" 234.50 --notes "Canetas, papel e post-its"
```

---

## 🔄 Reclassificar Transação

```bash
# Ver transações para encontrar o ID
stonks finance transactions

# Reclassificar transação 42 para "Alimentação"
stonks finance recategorize 42 Alimentação
```

**Nota:** O categorizador aprende com a reclassificação. Da próxima vez que uma transação similar for importada, ela será automaticamente categorizada como "Alimentação".

---

## 🎯 Metas Financeiras

```bash
# Criar meta de reserva de emergência
stonks goals create "Reserva de Emergência" 10000 \
    --deadline 2025-12-31 \
    --type savings \
    --priority high \
    --description "6 meses de despesas básicas"

# Criar meta de viagem
stonks goals create "Viagem Europa" 15000 \
    --deadline 2026-06-30 \
    --priority medium

# Listar metas ativas
stonks goals list

# Contribuir para meta
stonks goals contribute 1 500
stonks goals contribute 1 300

# Analisar meta com projeções e IA
stonks goals analyze 1
```

**Saída esperada do `goals analyze`:**
```
Análise da Meta: Reserva de Emergência

  Progresso: [████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 25.0%
  Acumulado: R$ 2.500,00 de R$ 10.000,00

┌──────────┬────────────────┬──────────────────┐
│ Cenário  │ Valor Mensal   │ Previsão         │
├──────────┼────────────────┼──────────────────┤
│ Otimista │ R$ 1.000/mês   │ Out/2025         │
│ Realista │ R$ 500/mês     │ Abr/2026         │
│ Conserv. │ R$ 250/mês     │ Jan/2028         │
└──────────┴────────────────┴──────────────────┘

Sugestão da IA:
Para atingir sua meta até dezembro de 2025, considere:
- Aumentar contribuição mensal para R$ 750
- Reduzir assinaturas não essenciais
- Destinar 30% do próximo bônus para a meta
```

---

## 📊 Dashboard Financeiro

```bash
# Dashboard do mês atual
stonks finance dashboard

# Dashboard de mês específico com análise IA
stonks finance dashboard --year 2025 --month 1 --ai
```

**Saída esperada:**
```
📊 Dashboard Financeiro — 01/2025

┌──────────────────┬──────────────┐
│ Indicador        │ Valor        │
├──────────────────┼──────────────┤
│ 💰 Receitas      │ R$ 8.500,00  │
│ 💸 Despesas      │ R$ 4.200,00  │
│ 📊 Saldo         │ R$ 4.300,00  │
│ 📈 Média Diária  │ R$ 135,48    │
│ 🔄 Transações    │ 47           │
└──────────────────┴──────────────┘

┌──────────────────────┬──────────────┬──────┐
│ Categoria            │ Valor        │ %    │
├──────────────────────┼──────────────┼──────┤
│ Moradia              │ R$ 1.200,00  │ 28,6 │
│ Alimentação          │ R$ 850,00    │ 20,2 │
│ Transporte           │ R$ 450,00    │ 10,7 │
│ Assinaturas          │ R$ 180,00    │ 4,3  │
└──────────────────────┴──────────────┴──────┘
```

---

## 🔔 Alertas Inteligentes

```bash
# Verificar alertas automaticamente
stonks alerts check

# Listar alertas ativos
stonks alerts list

# Dispensar alerta
stonks alerts dismiss 1
```

**Possíveis alertas:**
- 🔴 **Alta em alimentação:** Gastos 35% acima da média
- 🟡 **Saldo baixo:** Restam apenas R$ 200 até o próximo salário
- 🟢 **Assinatura alterada:** Netflix aumentou de R$ 39,90 para R$ 55,90

---

## 🗑️ Deletar Transação

```bash
# Listar para encontrar o ID
stonks finance transactions

# Remover transação
stonks finance delete 42
```

---

## 💬 Chat Financeiro com IA

```bash
# Pergunta única
stonks chat "O que é P/L e como interpretar?"
stonks chat "Qual a diferença entre CDB e Tesouro Direto?"
stonks chat "Como calcular reserva de emergência?"

# Modo interativo (conversa contínua)
stonks chat -i
```

---

## 🎯 Fluxo Completo: Análise de Finanças Pessoais

```bash
# 1. Inicializar sistema (primeira vez)
stonks init

# 2. Importar extratos bancários
stonks finance import extrato_nubank.csv
stonks finance import extrato_itau.xlsx

# 3. Ver dashboard financeiro
stonks finance dashboard --ai

# 4. Criar meta financeira
stonks goals create "Reserva de Emergência" 10000 \
    --deadline 2025-12-31 \
    --priority high

# 5. Verificar alertas
stonks alerts check

# 6. Analisar ações
stonks analyze PETR4
stonks compare PETR4 VALE3 BBAS3
```
