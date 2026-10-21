# Como a carteira calcula

Este documento explica as contas da tela **Carteira**: preço médio, posição, importação da B3
e rentabilidade. As decisões de arquitetura estão no [ADR 021](adr.md#adr-021-carteira-calculada-a-partir-das-operações-com-importação-dos-extratos-da-b3);
o código está em `stonks_ai/utils/portfolio.py`, `stonks_ai/utils/performance.py` e
`stonks_ai/collectors/finance/b3_importer.py`.

---

## 1. Preço médio (método da Receita Federal)

A regra em uma frase: **compra muda o preço médio; venda não muda.**

| Operação | Cotas | Custo total | Preço médio |
|---|---|---|---|
| Compra de 100 a R$ 10 + R$ 5 de taxa | 100 | 1.005,00 | 10,05 |
| Compra de 100 a R$ 20 + R$ 5 de taxa | 200 | 3.010,00 | **15,05** |
| Venda de 50 a R$ 30 − R$ 2 de taxa | 150 | 2.257,50 | **15,05** |
| Desdobramento 1:2 (recebe 150 cotas sem custo) | 300 | 2.257,50 | 7,525 |
| Grupamento 10:1 (270 cotas deixam de existir) | 30 | 2.257,50 | 75,25 |

- **Compra:** soma as cotas e soma ao custo o valor pago mais as taxas.
- **Venda:** as cotas saem da pilha pelo preço médio. Na venda acima você recebe R$ 1.498; as 50 cotas
  "custaram" 50 × 15,05 = R$ 752,50; o **lucro realizado** é R$ 745,50. O que sobra continua custando
  15,05 por cota, por isso o preço médio não muda.
- **Desdobramento e grupamento:** mudam só o número de cotas; o custo total fica igual. Mais fatias
  (ou menos) do mesmo bolo.
- **Bonificação:** soma cotas pelo **custo atribuído** que a empresa informa, então aumenta o custo total.
- **Proventos** (dividendos, JCP, rendimentos de FII) não mexem no preço médio; são somados à parte.

Esse é o mesmo cálculo exigido na declaração do Imposto de Renda (bens e direitos pelo custo de
aquisição). Teste: `test_average_price_includes_fees_and_sells_keep_it`.

## 2. Por que a posição não é guardada

Como o saldo de uma conta, que é a soma dos lançamentos, a posição é a soma das operações.
O banco guarda só as operações (`investment_operations`); quantidade, preço médio, lucro e proventos
são recalculados reaplicando todas, em ordem de data, a cada consulta (`build_positions`).

Se a posição ficasse guardada e você apagasse uma compra de 2021, o lucro de todas as vendas
seguintes mudaria, porque o preço médio daquela época muda. Seria preciso reprocessar o histórico do
mesmo jeito, e a posição guardada viraria uma segunda fonte de verdade que pode discordar da primeira.
Recalcular custa milissegundos mesmo com milhares de operações.

Detalhes:
- No mesmo dia, **compras entram antes das vendas**; sem isso, um day trade pareceria a venda de cotas
  que você não tinha.
- **Venda maior que as compras conhecidas** (comum quando a compra é anterior a novembro de 2019, onde
  o extrato da B3 começa): a posição é marcada como incompleta, a tela avisa e o lucro é calculado só
  sobre as cotas conhecidas.

## 3. Importação dos extratos da B3

**Qual extrato é qual.** O importador lê as 10 primeiras linhas da planilha, tira acentos, põe em
minúsculas e procura uma linha com **todas** as colunas esperadas:

| Extrato | Colunas que o identificam | O que vira operação |
|---|---|---|
| Negociação | "Data do Negócio", "Código de Negociação", "Tipo de Movimentação"… | Compras e vendas |
| Movimentação | "Entrada/Saída", "Movimentação", "Produto"… | Dividendos, JCP, rendimentos, desdobramentos, bonificações |

O nome do arquivo não importa (você pode renomeá-lo), e linhas de título acima do cabeçalho são
ignoradas.

**Por que a Movimentação não traz compras.** Ela também lista cada compra e venda, como
"Transferência - Liquidação", dois dias depois do pregão. Se as duas valessem, tudo contaria duas vezes.
A Negociação ganha porque tem a data do negócio, que é a que vale para o preço médio e para o IR.

**O que é ignorado** (e listado no aviso da importação): opções, termo, renda fixa, Tesouro, aluguel
de ações, frações e direitos. Grupamentos são lançados à mão. O código do mercado fracionário
(`PETR4F`) vira `PETR4`.

**Por que reimportar não duplica.** Cada linha ganha uma impressão digital (`import_key`): o hash de
data, ativo, tipo, quantidade, preço, valor, corretora e um **número de ordem** entre linhas idênticas.
Duas compras iguais no mesmo dia viram #1 e #2 e continuam duas; o mesmo arquivo importado de novo gera
as mesmas chaves, e o banco ignora as que já existem. Limite: se a B3 mudar algum texto da linha
(o nome da corretora, por exemplo), a chave muda e a linha entra de novo.

## 4. Rentabilidade com aportes ao longo do tempo

Quem investe aos poucos não tem uma rentabilidade "óbvia". Exemplo:

- Janeiro: investe R$ 1.000. Em junho vale R$ 1.100 (**+10%**).
- Junho: aporta mais R$ 10.000; total R$ 11.100.
- Dezembro: vale R$ 11.400. No segundo semestre rendeu 11.400 / 11.100, cerca de **+2,7%**.

| Método | Conta | Resultado |
|---|---|---|
| Simples (valor ÷ investido) | 11.400 / 11.000 | **+3,6%** |
| Ponderado no tempo | 1,10 × 1,027 | **+13,0%** |

- O **simples** mistura o desempenho dos ativos com *quando* você pôs dinheiro: quase tudo entrou no
  semestre fraco, então o número fica baixo. É o "resultado sobre o preço médio" das posições.
- O **ponderado no tempo** encadeia os trechos entre um aporte e outro e mede só as escolhas de
  investimento. É o número comparável ao **CDI** e ao **Ibovespa**, que não recebem aportes.
- É o sistema de **cotas** dos fundos: cada aporte "compra cotas" da carteira pelo valor do dia; o valor
  da cota só sobe ou desce com o rendimento.

### Como o app calcula

O gráfico "Rentabilidade" da Carteira usa o retorno ponderado no tempo, **dia a dia**
(`stonks_ai/utils/performance.py`):

1. Para cada pregão desde a primeira operação, aplica as operações do dia e calcula o valor da carteira
   com o fechamento de cada ativo.
2. O retorno do dia é

   ```
   r = (valor no fim do dia + vendas do dia + proventos do dia) / (valor do dia anterior + compras do dia) − 1
   ```

   Compras entram na base (o dinheiro novo estava lá o dia todo); vendas e proventos contam como saída de
   dinheiro que a carteira gerou. Dia sem dinheiro investido tem retorno zero.
3. Os retornos diários são encadeados: índice de hoje = índice de ontem × (1 + r).
4. **CDI:** taxa diária da série 12 do Banco Central (`api.bcb.gov.br`), encadeada do mesmo jeito.
   **Ibovespa:** fechamento do `^BVSP` no yfinance.
5. Também mostra o **% do CDI** (retorno da carteira ÷ retorno do CDI no mesmo período), o jeito comum
   de comparar investimentos no Brasil.

Cuidados:
- **Preços sem o ajuste de desdobramento.** O yfinance divide os preços antigos pelos desdobramentos e
  bonificações (ITSA4 aparece com "Stock Splits" de 1,05, 1,10…). Como a carteira usa as cotas que você
  tinha *naquele dia*, o app multiplica o preço de volta pelos eventos posteriores; senão um desdobramento
  apareceria como alta de 100% no dia.
- **Proventos entram na data de pagamento** (é a data do extrato da B3), mas a ação cai na data ex.
  Entre as duas datas a carteira parece um pouco pior; no mês fecha certo.
- **Sem taxas da B3 nos extratos**, o retorno real fica um pouco abaixo do calculado se houver
  corretagem.
- Ativo sem histórico de preços (código antigo, deslistado) é avaliado pelo preço da última operação, e
  a tela avisa.
- Provento pago depois de vender todas as cotas não entra na rentabilidade: naquele dia não há valor
  investido para servir de base. Ele continua somado nos proventos.
- Os dados de fora (preços, CDI, Ibovespa) ficam em memória por uma hora; o primeiro cálculo de cada
  sessão do app precisa de internet. Decisão registrada no [ADR 022](adr.md).
