# 🌐 Stonks AI — Site Público

## Estrutura

```
site/
├── landing/                  # Landing page estática
│   ├── index.html            # HTML — tema escuro, glassmorphism
│   ├── style.css             # CSS — design system completo
│   └── script.js             # JS — partículas, animações
│
├── dashboard/                # App interactivo (Streamlit)
│   ├── app.py                # Dashboard público
│   └── config.yaml           # Config específica do site
│
└── README.md                 # Este ficheiro
```

## 🚀 Deploy Grátis (Zero Orçamento)

### 1. Landing Page → GitHub Pages

```bash
# Opção A: Domínio próprio (recomendado)
# 1. Comprar domínio (ex: stonks.ai) — ~R$ 40/ano na Namecheap
# 2. Ir ao repo GitHub → Settings → Pages
# 3. Source: main branch, pasta /site/landing
# 4. Custom domain: stonks.ai
# 5. Adicionar CNAME no DNS

# Opção B: Subdomínio grátis
# 1. Settings → Pages → Source: main branch, /site/landing
# 2. URL: Miguel-Soares1.github.io/stonks-ai2.0/site/landing/
```

### 2. Dashboard → Streamlit Community Cloud

```bash
# 1. Ir a https://share.streamlit.io
# 2. Conectar conta GitHub
# 3. New App → selecionar repo stonks-ai
# 4. Main file path: site/dashboard/app.py
# 5. Deploy!
# 6. URL: stonksai.streamlit.app

# Configurar secrets no Streamlit Cloud:
# Settings → Secrets:
GEMINI_API_KEY = "sua-chave-gratuita-aqui"
```

### 3. IA Gratuita → Google Gemini

```bash
# 1. Ir a https://aistudio.google.com
# 2. Create API Key (grátis, 15 req/min)
# 3. Adicionar ao secrets do Streamlit Cloud
#    ou export GEMINI_API_KEY="..." para local
```

## 📊 Funcionalidades do Site

| Funcionalidade | Disponível | IA |
|---------------|-----------|-----|
| Cotação B3/NYSE | ✅ Grátis | — |
| Gráfico histórico | ✅ Grátis | — |
| Análise IA | ✅ Grátis | Google Gemini (grátis) |
| Comparação | ✅ Grátis | — |
| Finanças pessoais | ❌ Não | Privacidade |
| Extratos bancários | ❌ Não | Privacidade |

## 💰 Monetização (Quando Tiver Tráfego)

```yaml
# 1. Ads Contextuais (sem tracking)
#    - Carbon Ads: ~$2 CPM → ~$100/mês com 50k views
#    - EthicalAds: similar
#    - Basta 1 linha de script

# 2. Afiliados de Corretoras
#    - XP: R$ 15-30 por conta aberta
#    - Rico: R$ 15-25 por conta
#    - Clear: R$ 10-20 por conta
#    - Interactive Brokers: $5-10

# 3. Premium
#    - R$ 19/mês: IA avançada, alertas, sem ads
```

## 🔒 Privacidade

- **Zero cookies** de rastreamento
- **Zero partilha** de dados com terceiros
- **Código aberto** (MIT) — qualquer pessoa pode auditar
- **Análises de ações**: dados públicos, sem info pessoal
- **Finanças pessoais**: **nunca** disponíveis no site público
