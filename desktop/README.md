# Stonks AI Desktop

App nativo para Windows. Substituiu a antiga interface Streamlit, já removida.

```
StonksAI.exe
 └── janela nativa (pywebview → WebView2 do Windows)
       └── frontend/ (HTML + CSS + JS em módulos, sem etapa de build)
             └── API local FastAPI em 127.0.0.1, numa porta livre aleatória
                   └── agentes e banco que já existem em stonks_ai/
```

## Telas

| Área | Tela | O que faz |
|---|---|---|
| | Início | Saldo nas contas, quanto entrou e saiu, o mês em uma frase, ritmo de gastos, insight do mês (calculado pelo código; a IA só explica se você pedir), saldo em 90 dias, receitas e despesas dos últimos 6 meses, recorrentes, metas, watchlist e resumo do mês pela IA |
| Mercado | Ativos | Cotação, histórico (1M a 5A), fundamentos com explicação de cada indicador e análise pela IA. Abre pela busca **Ctrl K** |
| | Watchlist | Ativos acompanhados, preço-alvo e distância até ele |
| | Comparar | De 2 a 5 ativos: desempenho em base 100, indicadores lado a lado e comparação pela IA |
| Minhas finanças | Transações | Filtros, adicionar, editar e excluir. Importar extrato pelo botão ou **arrastando o arquivo para a janela**. Transações recorrentes (semanal, quinzenal, mensal, anual) são lançadas sozinhas quando a data chega |
| | Orçamento | Limite mensal por categoria e quanto já foi usado (substitui a aba Categorias). Regras de categoria aprendidas: ao corrigir a categoria de uma transação, o estabelecimento passa a ir sempre para ela |
| | Contas | Contas e cartões com saldo |
| | Metas | Criar, editar, adicionar valor e acompanhar prazo |
| | Alertas | Avisos de orçamento e metas; verificar agora e dispensar |
| Assistente | Conversar com a IA | Chat com histórico; a resposta aparece enquanto é escrita. A mesma conversa abre num painel flutuante pelo botão **Perguntar à IA**, sem sair da tela atual |
| | Ajustes | Provider e modelo de IA (lista os modelos do Ollama com o tamanho), bolsa padrão, informações do sistema |

Todas as respostas da IA chegam em **streaming**: o primeiro trecho aparece em menos de 1 segundo, em vez de esperar a resposta inteira.

## Rodar em modo desenvolvimento

```bash
pip install -e ".[desktop]"
python -m desktop.app
```

Para mexer só no visual, rode a API e abra no navegador (F5 recarrega):

```bash
uvicorn desktop.api:app --port 8765
# abra http://127.0.0.1:8765
```

Para testar sem tocar nos seus dados reais, aponte para outra pasta com `STONKS_DATA_DIR`.

## Gerar o executável

```bash
pyinstaller desktop/stonks-desktop.spec --noconfirm
```

O resultado fica em `dist/StonksAI/` (cerca de 260 MB).

Na primeira abertura, o app cria sozinho o banco, as categorias, as contas e os alertas padrão (o equivalente ao `stonks init`).

## Gerar o instalador

Com o [Inno Setup 6](https://jrsoftware.org/isinfo.php) instalado (`winget install JRSoftware.InnoSetup --scope user`):

```bash
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" desktop\installer\stonks-ai.iss
```

Gera `dist/installer/StonksAI-Setup-<versão>.exe`, em português:

- Instala só para o usuário atual, sem pedir administrador.
- Cria atalho no menu Iniciar e, se o usuário quiser, na área de trabalho.
- Aparece em "Aplicativos instalados" para desinstalar.
- Na desinstalação, **pergunta** se deve apagar também os dados financeiros. O padrão é manter.

Mantenha `AppVersion` do `.iss` igual à versão do `pyproject.toml`.

## Segurança

| Proteção | Como funciona |
|---|---|
| Token por sessão | O app gera um token aleatório a cada abertura e o entrega só à janela. Chamadas à API sem ele recebem 401, então outros programas ou sites abertos no navegador não leem seus dados. |
| Só endereço local | A API escuta em `127.0.0.1` e recusa requisições com outro `Host` (bloqueia DNS rebinding). |
| Cabeçalhos | Content-Security-Policy restrita (só scripts do próprio app, nada externo), `nosniff`, sem `Referer`, sem cache. |
| Janela em modo privado | A WebView não grava cache, cookies nem histórico das páginas em disco. |
| Respostas da IA | O texto é escapado antes de virar HTML; uma resposta maliciosa não consegue injetar scripts. |
| Bloqueio por PIN | Opcional (Ajustes). Com PIN, a API responde 423 a qualquer rota de dados até o PIN ser digitado, e bloqueia de novo após um tempo sem uso (5 min a 1 h, ou só ao abrir). O PIN fica como hash scrypt com sal; erros seguidos aumentam a espera. Não criptografa o banco: protege o app aberto, não os arquivos. Esqueceu o PIN? Com o app fechado, apague `pin_hash` em `config.yaml`. |
| Ocultar valores | O botão de olho no topo troca todos os valores pessoais por `R$ ••••`, inclusive nas respostas da IA. |
| Chave da IA no cofre | A chave de uma IA na nuvem fica no Gerenciador de Credenciais do Windows, não no `config.yaml` (que guarda só o marcador `@keyring`). Chaves salvas em texto puro por versões antigas são movidas ao abrir o app. |
| Backup | Cópia automática semanal (guarda as 8 últimas) em `backups/` dentro da pasta de dados, mais backup manual e restauração em Ajustes. Restaurar salva antes uma cópia do estado atual. |
| Extrato fica local | A categorização roda no próprio app (regras aprendidas e palavras-chave), sem enviar o extrato a nenhuma IA, mesmo com o chat configurado para uma IA na nuvem. |
| Importação | Só CSV, Excel e PDF, até 20 MB, processados numa pasta temporária apagada em seguida. |

Rodando a API à mão (`uvicorn desktop.api:app`), não há token: use só para desenvolvimento. Para testar com token, defina `STONKS_API_TOKEN` e abra `http://127.0.0.1:8765/?t=<token>`.

## Onde ficam os dados

| Modo | Pasta |
|---|---|
| Desenvolvimento | `data/` do projeto (como antes) |
| Executável | `%APPDATA%\StonksAI` |
| Qualquer modo | o que estiver em `STONKS_DATA_DIR`, se definido |

## Estrutura

```
desktop/
├── app.py            # abre a janela e sobe a API
├── api.py            # FastAPI: rotas + inicialização + frontend estático
├── state.py          # agentes compartilhados (recriados ao trocar a IA)
├── streaming.py      # respostas da IA em streaming sem travar o servidor
├── routes/           # finance.py, market.py, assistant.py, settings.py
└── frontend/
    ├── index.html, styles.css
    └── js/
        ├── main.js   # rotas (#tela/parametro), tema, Ctrl K, arrastar extrato
        ├── core.js   # formatação pt-BR, API, diálogos, avisos, markdown
        ├── charts.js # gráficos SVG (linha e barras)
        └── views/    # uma tela por arquivo
```

## API

| Rota | O que faz |
|---|---|
| `GET /api/status` | IA disponível, provider/modelo e pasta de dados |
| `GET /api/dashboard?year=&month=` | Resumo do mês, mês anterior, saldo de 90 dias, metas e alertas |
| `GET /api/dashboard/summary-ai?year=&month=` | Resumo do mês pela IA (streaming) |
| `GET /api/months?count=6` | Receitas e despesas dos últimos meses |
| `GET /api/asset/{ticker}?period=` | Cotação, fundamentos e histórico |
| `GET /api/asset/{ticker}/history?period=` | Só o histórico |
| `GET /api/asset/{ticker}/analysis` | Análise pela IA (streaming) |
| `GET/POST /api/watchlist`, `PATCH/DELETE /api/watchlist/{id}` | Watchlist |
| `GET /api/compare?tickers=&period=` | Comparação em base 100 |
| `GET /api/compare/analysis?tickers=` | Comparação pela IA (streaming) |
| `GET/POST /api/transactions`, `PUT/DELETE /api/transactions/{id}` | Transações |
| `POST /api/import?filename=` | Importar extrato (o corpo é o arquivo) |
| `GET /api/categories`, `GET /api/budget`, `PUT /api/categories/{id}/budget` | Orçamento |
| `GET/POST /api/accounts`, `PUT/DELETE /api/accounts/{id}` | Contas |
| `GET/POST /api/goals`, `PUT/DELETE /api/goals/{id}`, `POST /api/goals/{id}/contribute` | Metas |
| `GET /api/alerts`, `POST /api/alerts/check`, `POST /api/alerts/{id}/dismiss` | Alertas |
| `POST /api/chat` | Conversa com a IA (streaming) |
| `GET/PUT /api/settings`, `GET /api/settings/ollama-models` | Ajustes |
| `GET /api/boot` | Tema, ocultar valores e estado do bloqueio (liberada com o app bloqueado) |
| `GET /api/lock`, `POST /api/lock/unlock`, `POST /api/lock/lock`, `PUT /api/lock/pin`, `PUT /api/lock/timeout` | Bloqueio por PIN |
| `PUT /api/settings/hide-values` | Ocultar valores |
| `GET /api/category-rules`, `DELETE /api/category-rules/{estabelecimento}` | Regras de categoria aprendidas |
| `GET/POST /api/backups`, `POST /api/backups/{nome}/restore` | Listar, criar e restaurar backups |
| `POST /api/backups/restore-file`, `POST /api/backups/open-folder` | Restaurar de um arquivo `.db`; abrir a pasta no Explorer |

## Próximos passos

1. Assinar o executável e o instalador (reduz alertas do antivírus e do SmartScreen).
2. Levar os testes ponta a ponta (Playwright) para dentro do repositório e rodá-los no CI. O painel flutuante do chat ainda não foi testado com clique.
3. Usar a IA local só para estabelecimentos sem regra de categoria, com cache por estabelecimento (ADR 020).
4. Windows Hello no lugar do PIN.
