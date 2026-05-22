"""Categorizador automático de transações financeiras.

Usa regex + keywords como primeira linha, com fallback para IA (Ollama)
quando não consegue classificar. Inclui aprendizado por reclassificação do usuário.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from stonks_ai.database import db
from stonks_ai.models.category import Category, DEFAULT_CATEGORIES
from stonks_ai.models.transaction import Transaction


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
            from stonks_ai.llm.client import OllamaClient

            llm = OllamaClient()
            if not llm.is_available():
                return None, "Sem categoria"

            cat_names = [c["name"] for c in available_categories]

            prompt = (
                f"Classifique a transação abaixo em UMA das categorias: "
                f"{', '.join(cat_names)}.\n\n"
                f"Descrição: '{description}'\n\n"
                "Responda APENAS com o nome exato da categoria, sem pontuação ou texto extra."
            )

            response = llm.generate(prompt).strip()

            # Tenta encontrar a categoria pelo nome retornado
            for cat in available_categories:
                if cat["name"].lower() in response.lower():
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
