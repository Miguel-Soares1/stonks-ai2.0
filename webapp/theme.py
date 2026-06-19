"""
Tema CSS escuro do Stonks AI — Glassmorphism + Animações.

Design profissional com:
- Efeito glass (backdrop-filter blur)
- Animações suaves de hover
- Gradientes verdes para destaque
- Cards com sombras e bordas translúcidas
- Responsivo e legível
"""


def get_theme_css() -> str:
    return """
<style>
    :root {
        --bg-deep: #050508;
        --bg-primary: #0a0a0f;
        --bg-secondary: #0d0d15;
        --bg-card: rgba(17, 17, 24, 0.65);
        --bg-card-hover: rgba(22, 22, 37, 0.8);
        --bg-input: rgba(17, 17, 24, 0.5);

        --border: #1a1a2e;
        --border-accent: #1a3a2a;
        --border-hover: #2a4a3a;

        --text-primary: #e8e8ed;
        --text-secondary: #a0a0b0;
        --text-muted: #606078;

        --accent: #00c853;
        --accent-light: #00e676;
        --accent-dark: #009624;
        --accent-glow: rgba(0, 200, 83, 0.12);
        --accent-glow-strong: rgba(0, 200, 83, 0.25);

        --positive: #00c853;
        --negative: #ff1744;
        --warning: #ffab00;
        --neutral: #a0a0b0;

        --ai-box-bg: rgba(0, 200, 83, 0.03);
        --ai-box-border: rgba(0, 200, 83, 0.1);

        --gradient-accent: linear-gradient(135deg, #00c853, #00e676);
        --gradient-hero: radial-gradient(ellipse at 50% 0%, rgba(0,200,83,0.05) 0%, transparent 70%);

        --radius-sm: 8px;
        --radius: 12px;
        --radius-lg: 20px;

        --shadow-card: 0 2px 12px rgba(0,0,0,0.3);
        --shadow-card-hover: 0 8px 32px rgba(0,0,0,0.4), 0 0 32px var(--accent-glow);
        --shadow-button: 0 4px 20px var(--accent-glow);

        --font-sans: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
    }

    /* ── App Background ────────────────────────────── */
    .stApp {
        background: linear-gradient(180deg, var(--bg-deep) 0%, var(--bg-primary) 50%, var(--bg-deep) 100%);
    }
    .main > div {
        background: transparent;
    }

    /* ── Typography ────────────────────────────────── */
    .main-header {
        font-size: 2.5rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: var(--text-primary);
        margin-bottom: 0.3rem;
    }
    .sub-header {
        font-size: 1.15rem;
        color: var(--text-secondary);
        margin-bottom: 2rem;
        line-height: 1.6;
    }
    p, h1, h2, h3, h4, h5, h6, span, label, li {
        color: var(--text-primary);
        font-family: var(--font-sans);
    }

    /* ── Glass Card ────────────────────────────────── */
    .glass-card {
        background: var(--bg-card);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 1.6rem;
        transition: all 0.3s ease;
        box-shadow: var(--shadow-card);
    }
    .glass-card:hover {
        background: var(--bg-card-hover);
        border-color: var(--border-accent);
        box-shadow: var(--shadow-card-hover);
        transform: translateY(-2px);
    }

    /* ── Metric Cards ──────────────────────────────── */
    .metric-card {
        background: var(--bg-card);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1.3rem;
        text-align: center;
        transition: all 0.3s ease;
    }
    .metric-card:hover {
        border-color: var(--border-accent);
        box-shadow: 0 4px 24px var(--accent-glow);
        transform: translateY(-2px);
    }
    .metric-label {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--text-muted);
        margin-bottom: 0.4rem;
        font-weight: 600;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: var(--text-primary);
    }
    .metric-value.positive { color: var(--positive); }
    .metric-value.negative { color: var(--negative); }
    .metric-value.neutral  { color: var(--neutral); }

    /* ── Info Box ──────────────────────────────────── */
    .info-box {
        background: var(--bg-card);
        backdrop-filter: blur(12px);
        border-radius: var(--radius);
        padding: 1rem 1.2rem;
        border-left: 4px solid var(--accent);
        margin: 0.8rem 0;
        box-shadow: var(--shadow-card);
    }

    /* ── AI Analysis Box ───────────────────────────── */
    .ai-box {
        background: var(--ai-box-bg);
        border: 1px solid var(--ai-box-border);
        border-radius: 16px;
        padding: 2rem;
        line-height: 1.8;
        font-size: 1.02rem;
        color: var(--text-primary);
    }

    /* ── Buttons ───────────────────────────────────── */
    .stButton > button {
        border-radius: var(--radius) !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        font-family: var(--font-sans) !important;
        border: none !important;
    }
    .stButton > button[kind="primary"] {
        background: var(--gradient-accent) !important;
        color: #000 !important;
        font-weight: 700 !important;
        box-shadow: var(--shadow-button) !important;
    }
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 8px 32px var(--accent-glow-strong) !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button[kind="secondary"] {
        background: rgba(255,255,255,0.04) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border) !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background: rgba(255,255,255,0.08) !important;
        border-color: var(--border-hover) !important;
    }

    /* ── Inputs ────────────────────────────────────── */
    .stTextInput input, .stNumberInput input {
        background: var(--bg-input) !important;
        backdrop-filter: blur(8px) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        color: var(--text-primary) !important;
        padding: 10px 14px !important;
        font-family: var(--font-sans) !important;
    }
    .stTextInput input:focus, .stSelectbox div:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px var(--accent-glow) !important;
    }
    .stTextInput input::placeholder {
        color: var(--text-muted) !important;
    }

    /* Selectbox — caixas de selecao maiores e legiveis */
    .stSelectbox > div > div {
        background: var(--bg-input) !important;
        backdrop-filter: blur(8px) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
    }
    .stSelectbox [data-baseweb="select"] {
        background: transparent !important;
    }
    .stSelectbox [data-baseweb="select"] [role="combobox"] {
        color: var(--text-primary) !important;
        font-family: var(--font-sans) !important;
        font-size: 0.95rem !important;
        padding: 8px 12px !important;
    }
    .stSelectbox [data-baseweb="select"] [role="combobox"]:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px var(--accent-glow) !important;
    }

    /* ── Tabs ──────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: var(--bg-secondary);
        padding: 6px;
        border-radius: var(--radius);
        border: 1px solid var(--border);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: var(--radius-sm) !important;
        padding: 10px 22px !important;
        font-weight: 600 !important;
        transition: all 0.3s !important;
        color: var(--text-secondary) !important;
        font-family: var(--font-sans) !important;
    }
    .stTabs [aria-selected="true"] {
        background: var(--gradient-accent) !important;
        color: #000 !important;
    }

    /* ── Sidebar ───────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: rgba(5, 5, 8, 0.95) !important;
        backdrop-filter: blur(30px) !important;
        -webkit-backdrop-filter: blur(30px) !important;
        border-right: 1px solid var(--border) !important;
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3, [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label {
        color: var(--text-primary) !important;
    }

    /* Sidebar nav buttons */
    [data-testid="stSidebar"] .stButton button {
        background: transparent !important;
        border: none !important;
        padding: 10px 14px !important;
        border-radius: var(--radius) !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        text-align: left !important;
        color: var(--text-secondary) !important;
        transition: all 0.2s !important;
        box-shadow: none !important;
        width: 100% !important;
        justify-content: flex-start !important;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background: rgba(0,200,83,0.06) !important;
        color: var(--accent-light) !important;
    }

    /* ── Nav Indicator ─────────────────────────────── */
    .nav-active-indicator {
        width: 3px;
        height: 28px;
        background: var(--gradient-accent);
        border-radius: 0 4px 4px 0;
        margin: 4px 0;
        box-shadow: 0 0 12px var(--accent-glow);
        flex-shrink: 0;
    }

    /* ── Chat ──────────────────────────────────────── */
    .stChatInputContainer { max-width: 100%; }
    [data-testid="stChatMessage"] {
        background: var(--bg-card) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-lg) !important;
        padding: 0.8rem 1.2rem !important;
        margin-bottom: 0.6rem !important;
    }
    .stChatInputContainer textarea {
        background: var(--bg-input) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        color: var(--text-primary) !important;
    }

    /* ── DataFrames ────────────────────────────────── */
    [data-testid="stDataFrame"] {
        border-radius: var(--radius-lg) !important;
        overflow: hidden !important;
        border: 1px solid var(--border) !important;
    }

    /* ── DataFrames internals ──────────────────────── */
    [data-testid="stDataFrame"] table {
        background: transparent !important;
    }
    [data-testid="stDataFrame"] th {
        background: rgba(0,0,0,0.3) !important;
        color: var(--text-muted) !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
        text-transform: uppercase !important;
    }
    [data-testid="stDataFrame"] td {
        color: var(--text-primary) !important;
        border-bottom: 1px solid rgba(255,255,255,0.03) !important;
    }

    /* ── Progress ──────────────────────────────────── */
    .stProgress > div > div {
        background: var(--gradient-accent) !important;
        border-radius: 4px !important;
    }
    .stProgress > div {
        background: rgba(255,255,255,0.05) !important;
        border-radius: 4px !important;
    }

    /* ── Spinner ───────────────────────────────────── */
    .stSpinner > div {
        border-top-color: var(--accent) !important;
        border-left-color: var(--accent) !important;
    }

    /* ── Expander ──────────────────────────────────── */
    .streamlit-expanderHeader {
        background: var(--bg-card) !important;
        border-radius: var(--radius) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
    }

    /* ── Slider ────────────────────────────────────── */
    .stSlider div[data-baseweb="slider"] div {
        background: var(--accent) !important;
    }

    /* ── Notifications ─────────────────────────────── */
    div[data-testid="stNotification"] {
        background: var(--bg-card) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
    }

    /* ── Pre / Code ────────────────────────────────── */
    .stCodeBlock {
        background: rgba(0,0,0,0.4) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
    }
    .stCodeBlock code {
        color: var(--accent-light) !important;
    }

    /* ── Select / Multiselect ──────────────────────── */
    .stSelectbox [data-baseweb="popover"] {
        background: var(--bg-card) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
    }

    /* ── Containers ────────────────────────────────── */
    [data-testid="stVerticalBlock"] > div > div > div[data-testid="stVerticalBlock"] {
        gap: 0.5rem;
    }

    /* ── Scrollbar ─────────────────────────────────── */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: var(--bg-secondary); }
    ::-webkit-scrollbar-thumb {
        background: var(--border);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover { background: var(--accent-dark); }

    /* ── Metrics (Streamlit built-in) ───────────────── */
    [data-testid="stMetric"] {
        background: var(--bg-card) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid var(--border) !important;
        border-radius: 16px !important;
        padding: 1rem !important;
    }
    [data-testid="stMetric"]:hover {
        border-color: var(--border-accent) !important;
        box-shadow: 0 4px 24px var(--accent-glow) !important;
    }
    [data-testid="stMetricValue"] {
        color: var(--text-primary) !important;
    }
    [data-testid="stMetricDelta"] {
        color: var(--positive) !important;
    }

    /* ── Mobile ────────────────────────────────────── */
    @media (max-width: 768px) {
        .main-header { font-size: 1.8rem; }
        .metric-value { font-size: 1.3rem; }
    }
</style>
"""
