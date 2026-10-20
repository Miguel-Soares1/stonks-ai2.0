"""Categorizador automático de transações financeiras.

Usa regex + keywords como primeira linha, com fallback para IA (Ollama)
quando não consegue classificar. Inclui aprendizado por reclassificação do usuário.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from stonks_ai.database import db
from stonks_ai.models.category import Category, DEFAULT_CATEGORIES
from stonks_ai.models.transaction import Transaction


# O que entra em cada categoria padrão. Modelos pequenos erram muito sem isso
# (ex.: conta de luz em "Assinaturas", streaming em "Lazer").
CATEGORY_HINTS = {
    "Alimentação": "mercado, atacado, padaria, restaurante, lanchonete, delivery de comida",
    "Transporte": "aplicativos de corrida, táxi, combustível, estacionamento, ônibus, metrô, despesas com veículo e estradas",
    "Moradia": "aluguel, condomínio, IPTU, contas de consumo da casa (energia, água, gás)",
    "Assinaturas": "streaming de vídeo ou música e outros serviços digitais cobrados todo mês",
    "Saúde": "drogaria, remédios, plano de saúde, consultas, exames",
    "Lazer": "cinema, shows, jogos e lojas de jogos digitais, passeios, bares",
    "Educação": "escola, faculdade, cursos e plataformas de ensino, livros",
    "Salário": "salário ou pagamento recebido do empregador",
    "Transferências": "Pix, TED ou DOC enviados ou recebidos entre pessoas",
    "Investimentos": "aplicações, resgates, compra e venda de ações, títulos ou fundos, corretoras",
    "Outros": "use somente se nenhuma outra categoria servir",
}

# Exemplos com marcas diferentes das usadas na avaliação (evals/casos.jsonl)
_CATEGORY_EXAMPLES = (
    "'MC DONALDS 0231' -> Alimentação\n"
    "'SHELL SELECT POSTO' -> Transporte\n"
    "'HBO MAX' -> Assinaturas"
)


def build_categorization_prompt(description: str, category_names: List[str]) -> str:
    """Prompt usado para classificar uma transação com IA (também usado em evals/)."""
    lines = [f"- {n}: {CATEGORY_HINTS[n]}" if n in CATEGORY_HINTS else f"- {n}" for n in category_names]
    return (
        "Classifique a transação de extrato bancário em UMA das categorias abaixo.\n\n"
        "Categorias:\n" + "\n".join(lines) + "\n\n"
        f"Exemplos:\n{_CATEGORY_EXAMPLES}\n\n"
        f"Transação: '{description}'\n\n"
        "Responda APENAS com o nome exato de uma categoria, sem pontuação ou texto extra."
    )


def parse_category(response: str, category_names: List[str]) -> Optional[str]:
    """Extrai a categoria da resposta do modelo.

    Prefere a resposta exata; senão, a categoria citada primeiro no texto
    (e não a primeira da lista, que viciava tudo em "Alimentação").
    """
    clean = response.strip().strip(".'\"").lower()
    for name in category_names:
        if clean == name.lower():
            return name
    found = [(response.lower().find(n.lower()), n) for n in category_names]
    found = [(pos, n) for pos, n in found if pos >= 0]
    return min(found)[1] if found else None


class Categorizer:
    """
    Classificador automático de transações financeiras.

    Pipeline:
    1. Regex + keywords (rápido, sem dependência externa)
    2. IA/Ollama (fallback para descrições ambíguas)
    3. Aprendizado (usuário reclassifica → sistema aprende)
    """

    def __init__(self):
        self._cached_categories: Optional[List[Dict[str, Any]]] = None
        self._llm_cache: Dict[str, Tuple[int, str]] = {}

    def _load_categories(self) -> List[Dict[str, Any]]:
        """Carrega categorias do banco com cache (como dicts, evitando detached ORM)."""
        if self._cached_categories is None:
            try:
                with db.session() as session:
                    cats = (
                        session.query(Category)
                        .order_by(Category.sort_order)
                        .all()
                    )
                    self._cached_categories = [
                        {
                            "id": c.id,
                            "name": c.name,
                            "keywords": json.loads(c.keywords) if c.keywords else [],
                        }
                        for c in cats
                    ]
            except Exception:
                self._cached_categories = []
        return self._cached_categories

    def categorize(self, description: str) -> Tuple[Optional[int], str]:
        """
        Classifica uma transação pela descrição usando regex + keywords.

        Returns:
            Tuple (category_id, category_name)
        """
        desc_upper = description.upper()
        categories = self._load_categories()

        # Tenta match com keywords de cada categoria
        for cat in categories:
            keywords_list = cat.get("keywords", [])
            for kw in keywords_list:
                if kw.upper() in desc_upper:
                    return cat["id"], cat["name"]

        # Categoria padrão "Outros"
        for cat in categories:
            if cat["name"] == "Outros":
                return cat["id"], "Outros"

        return None, "Sem categoria"

    def categorize_with_llm(
        self, description: str, available_categories: List[Dict]
    ) -> Tuple[Optional[int], str]:
        """
        Classifica usando IA quando regex não encontra match.

        Args:
            description: Descrição da transação.
            available_categories: Lista de categorias disponíveis.

        Returns:
            Tuple (category_id, category_name)
        """
        # Verifica cache
        cache_key = description.upper().strip()
        if cache_key in self._llm_cache:
            return self._llm_cache[cache_key]

        try:
            from stonks_ai.llm.client import get_local_llm_client

            llm = get_local_llm_client()
            if not llm.is_available():
                return None, "Sem categoria"

            cat_names = [c["name"] for c in available_categories]

            prompt = build_categorization_prompt(description, cat_names)

            response = llm.generate(prompt).strip()

            # Tenta encontrar a categoria pelo nome retornado
            chosen = parse_category(response, cat_names)
            for cat in available_categories:
                if cat["name"] == chosen:
                    result = (cat.get("id"), cat["name"])
                    self._llm_cache[cache_key] = result
                    return result

        except Exception:
            pass

        return None, "Sem categoria"

    def learn_from_reclassification(
        self, transaction_id: int, new_category_name: str
    ) -> bool:
        """
        Aprende com reclassificação manual do usuário.

        Quando o usuário reclassifica uma transação, adiciona keywords
        da descrição à categoria escolhida.

        Args:
            transaction_id: ID da transação reclassificada.
            new_category_name: Nome da nova categoria.

        Returns:
            bool: True se aprendeu com sucesso.
        """
        try:
            with db.session() as session:
                tx = session.query(Transaction).get(transaction_id)
                if not tx:
                    return False

                cat = session.query(Category).filter(
                    Category.name == new_category_name
                ).first()
                if not cat:
                    return False

                # Extrai palavras-chave relevantes da descrição
                desc_upper = tx.description.upper()
                words = [
                    w.strip() for w in desc_upper.split()
                    if len(w.strip()) > 3 and not any(
                        kw in w.strip() for kw in ["DE", "DA", "DO", "NA", "NO", "EM", "COM", "POR", "PARA"]
                    )
                ]

                if not words:
                    return False

                # Adiciona palavras à lista de keywords da categoria
                current_keywords = []
                if cat.keywords:
                    try:
                        current_keywords = json.loads(cat.keywords)
                    except (json.JSONDecodeError, TypeError):
                        current_keywords = []

                new_keywords = []
                for word in words[:5]:  # Máximo 5 palavras
                    if word not in current_keywords and word not in new_keywords:
                        new_keywords.append(word)

                if new_keywords:
                    current_keywords.extend(new_keywords)
                    cat.keywords = json.dumps(current_keywords)
                    session.add(cat)

                # Atualiza categoria da transação
                tx.category_id = cat.id
                tx.category_name = cat.name
                session.add(tx)

            # Invalida cache de categorias
            self._cached_categories = None
            return True

        except Exception:
            return False

    @staticmethod
    def initialize_default_categories() -> int:
        """
        Inicializa categorias padrão no banco de dados (se não existirem).

        Returns:
            Número de categorias criadas.
        """
        created = 0
        try:
            with db.session() as session:
                existing = session.query(Category).count()
                if existing > 0:
                    return 0

                for cat_data in DEFAULT_CATEGORIES:
                    cat = Category(**cat_data)
                    session.add(cat)
                    created += 1

            return created
        except Exception:
            return 0
