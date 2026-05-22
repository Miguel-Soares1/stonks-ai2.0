"""Modelo de categorias financeiras para classificação de gastos."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from stonks_ai.database import Base


class Category(Base):
    """Categoria para classificação automática de transações financeiras."""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    icon = Column(String(10), nullable=False, default="📦")
    keywords = Column(Text, nullable=True)  # JSON list: ["IFOOD", "RESTAURANTE", ...]
    parent_id = Column(Integer, nullable=True)  # Auto-referência para subcategorias
    budget_limit = Column(Integer, nullable=True)  # Limite mensal em centavos
    budget_period = Column(String(20), nullable=False, default="monthly")  # monthly, weekly, yearly
    color = Column(String(7), nullable=True)  # Hex color #FF5733
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self) -> str:
        return f"<Category(name='{self.name}', icon='{self.icon}')>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "keywords": self.keywords,
            "parent_id": self.parent_id,
            "budget_limit": self.budget_limit,
            "budget_period": self.budget_period,
            "color": self.color,
            "sort_order": self.sort_order,
        }


# Categorias padrão para inicialização
DEFAULT_CATEGORIES = [
    {"name": "Alimentação", "icon": "🍕", "keywords": '["IFOOD", "RESTAURANTE", "MCDONALDS", "BURGER", "PIZZA", "ACAI", "PADARIA", "SUPERMERCADO", "MERCADO", "FEIRA", "HORTIFRUTI", "ASSAl", "ST MARTHA", "CARREFOUR"]', "color": "#FF6B35", "sort_order": 1},
    {"name": "Transporte", "icon": "🚗", "keywords": '["UBER", "99TAXI", "PEDAGIO", "COMBUSTIVEL", "POSTO", "GASOLINA", "DIESEL", "ETANOL", "ESTACIONAMENTO", "CARRO", "OFICINA", "MANUTENCAO"]', "color": "#004E89", "sort_order": 2},
    {"name": "Moradia", "icon": "🏠", "keywords": '["ALUGUEL", "CONDOMINIO", "IPTU", "AGUA", "LUZ", "ENERGIA", "CEA", "CPFL", "INTERNET", "TV POR ASSINATURA"]', "color": "#1A659E", "sort_order": 3},
    {"name": "Assinaturas", "icon": "📺", "keywords": '["NETFLIX", "SPOTIFY", "STEAM", "DISNEY", "AMAZON PRIME", "HBO", "APPLE TV", "DEEZER", "YOUTUBE PREMIUM", "CANAL+", "CLARO TV"]', "color": "#FF006E", "sort_order": 4},
    {"name": "Saúde", "icon": "💊", "keywords": '["FARMACIA", "DROGARIA", "PAGUE MENOS", "DROGA RAIA", "MEDICO", "CONSULTA", "EXAME", "PLANO DE SAUDE", "UNIMED", "BRADESCO SAUDE", "DENTISTA", "PSICOLOGO"]', "color": "#00A896", "sort_order": 5},
    {"name": "Lazer", "icon": "🎮", "keywords": '["CINEMA", "SHOW", "INGRESSO", "JOGO", "GAMES", "PLAYSTATION", "XBOX", "CINEMARK", "CINESYSTEM", "TEATRO", "PARQUE", "MUSEU"]', "color": "#8338EC", "sort_order": 6},
    {"name": "Educação", "icon": "📚", "keywords": '["CURSO", "FACULDADE", "UNIVERSIDADE", "ENSINO", "ESCOLA", "CURSOS ONLINE", "UDEMY", "COURSERA", "ALURA", "CULTURA INGLESA", "WIZARD"]', "color": "#3A86FF", "sort_order": 7},
    {"name": "Salário", "icon": "💰", "keywords": '["SALARIO", "PAGAMENTO", "HONORARIO", "PROVENTOS", "DECIMO", "FERIAS", "BONUS", "COMISSAO"]', "color": "#06D6A0", "sort_order": 8},
    {"name": "Transferências", "icon": "🔄", "keywords": '["PIX", "TED", "DOC", "TRANSFERENCIA", "POUPANCA"]', "color": "#118AB2", "sort_order": 9},
    {"name": "Investimentos", "icon": "📈", "keywords": '["INVESTIMENTO", "RENDA FIXA", "CDB", "LCI", "LCA", "TESOURO", "AÇÕES", "BOLSA", "B3", "NU INVEST", "XP", "BTG", "EASINVEST"]', "color": "#0D3B66", "sort_order": 10},
    {"name": "Outros", "icon": "📦", "keywords": '[]', "color": "#6C757D", "sort_order": 99},
]
