"""Categorizador automático de transações financeiras.

Ordem de decisão (a mesma para importação, transação manual e edição):

1. Regra aprendida: quando o usuário corrige a categoria de uma transação, o
   estabelecimento (ex.: "PANVEL FARMACIAS") passa a ir sempre para a categoria escolhida.
2. Palavras-chave da categoria, como palavra inteira ("DOC" não casa com "DOCES"),
   ganhando a mais específica ("UBER EATS" vence "UBER").
3. "Outros".

A IA (categorize_with_llm) fica disponível para quem quiser chamá-la, mas não entra no
fluxo de importação: com centenas de linhas, cada chamada ao modelo local pesa.
"""

import json
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from stonks_ai.database import db
from stonks_ai.models.category import Category, DEFAULT_CATEGORIES
from stonks_ai.models.transaction import Transaction
from stonks_ai.models.user_preferences import UserPreference

RULE_PREFIX = "cat_rule:"

# Partes de descrição de extrato que não identificam o estabelecimento
_NOISE_PREFIXES = (
    "COMPRA CARTAO DEBITO", "COMPRA CARTAO CREDITO", "COMPRA CARTAO", "COMPRA NO DEBITO",
    "COMPRA NO CREDITO", "COMPRA DEBITO", "COMPRA CREDITO", "COMPRA", "PAG", "PAGTO", "DEB AUT",
    "DEBITO AUTOMATICO",
)
_NOISE_WORDS = {
    "LJ", "LOJA", "FILIAL", "PARC", "PARCELA", "BR", "SAO", "SP", "RJ", "MG", "LTDA", "ME", "SA", "EIRELI",
    "DE", "DA", "DO", "DAS", "DOS",
}

# Cache compartilhado entre instâncias (agente e importadores): uma regra aprendida
# pelo agente vale na próxima importação sem reiniciar o app.
_cache: Dict[str, Any] = {"categories": None, "rules": None}


def invalidate_cache() -> None:
    _cache["categories"] = None
    _cache["rules"] = None


def normalize(text: str) -> str:
    """Maiúsculas, sem acentos e com espaços simples (para comparar descrições)."""
    no_accents = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", no_accents.upper()).strip()


def merchant_key(description: str) -> str:
    """
    Identifica o estabelecimento numa descrição de extrato.

    "COMPRA CARTAO PANVEL FARMACIAS LJ 33 20/10" -> "PANVEL FARMACIAS"
    "UBER *TRIP 8842" -> "UBER TRIP"
    """
    text = normalize(description)
    for prefix in _NOISE_PREFIXES:
        if text.startswith(prefix + " ") or text.startswith(prefix + "*"):
            text = text[len(prefix):]
            break
    words = [w for w in re.split(r"[^A-Z0-9]+", text) if w]
    words = [w for w in words if not any(c.isdigit() for c in w) and w not in _NOISE_WORDS and len(w) > 1]
    return " ".join(words[:3])


def _keyword_regex(keyword: str) -> "re.Pattern[str]":
    # Palavra inteira, aceitando plural com S ("FARMACIA" casa com "FARMACIAS")
    return re.compile(rf"(?<![A-Z0-9]){re.escape(normalize(keyword))}S?(?![A-Z0-9])")


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
        self._llm_cache: Dict[str, Tuple[int, str]] = {}

    @staticmethod
    def _load_categories() -> List[Dict[str, Any]]:
        """Carrega categorias do banco com cache (como dicts, evitando detached ORM)."""
        if _cache["categories"] is None:
            try:
                with db.session() as session:
                    cats = session.query(Category).order_by(Category.sort_order).all()
                    loaded = []
                    for c in cats:
                        try:
                            keywords = json.loads(c.keywords) if c.keywords else []
                        except (json.JSONDecodeError, TypeError):
                            keywords = []
                        loaded.append({
                            "id": c.id,
                            "name": c.name,
                            "keywords": [(len(normalize(k)), _keyword_regex(k)) for k in keywords if k.strip()],
                        })
                    _cache["categories"] = loaded
            except Exception:
                _cache["categories"] = []
        return _cache["categories"]

    @staticmethod
    def _load_rules() -> Dict[str, str]:
        """Regras aprendidas: estabelecimento -> nome da categoria."""
        if _cache["rules"] is None:
            try:
                with db.session() as session:
                    prefs = session.query(UserPreference).filter(
                        UserPreference.key.like(f"{RULE_PREFIX}%")
                    ).all()
                    _cache["rules"] = {p.key[len(RULE_PREFIX):]: p.value for p in prefs}
            except Exception:
                _cache["rules"] = {}
        return _cache["rules"]

    def categorize(self, description: str) -> Tuple[Optional[int], str]:
        """
        Classifica uma transação: regra aprendida, depois palavra-chave mais específica.

        Returns:
            Tuple (category_id, category_name)
        """
        categories = self._load_categories()
        by_name = {c["name"]: c for c in categories}

        learned = self._load_rules().get(merchant_key(description))
        if learned in by_name:
            return by_name[learned]["id"], learned

        text = normalize(description)
        best: Optional[Tuple[int, Dict[str, Any]]] = None
        for cat in categories:
            for length, pattern in cat["keywords"]:
                if (best is None or length > best[0]) and pattern.search(text):
                    best = (length, cat)
        if best:
            return best[1]["id"], best[1]["name"]

        if "Outros" in by_name:
            return by_name["Outros"]["id"], "Outros"
        return None, "Sem categoria"

    def learn(self, description: str, category_name: str, previous_category: Optional[str] = None) -> int:
        """
        Guarda a regra "este estabelecimento vai para esta categoria".

        Transações do mesmo estabelecimento que estavam na mesma categoria antiga (ou seja,
        que foram classificadas pelo mesmo engano) são corrigidas junto.

        Returns:
            Quantas outras transações foram recategorizadas.
        """
        key = merchant_key(description)
        if not key:
            return 0
        with db.session() as session:
            cat = session.query(Category).filter(Category.name == category_name).first()
            if not cat:
                return 0
            pref = session.query(UserPreference).filter(UserPreference.key == RULE_PREFIX + key).first()
            if pref:
                pref.value = cat.name
            else:
                session.add(UserPreference(key=RULE_PREFIX + key, value=cat.name))

            fixed = 0
            if previous_category and previous_category != cat.name:
                same_before = session.query(Transaction).filter(
                    Transaction.category_name == previous_category
                ).all()
                for tx in same_before:
                    if merchant_key(tx.description) == key:
                        tx.category_id = cat.id
                        tx.category_name = cat.name
                        fixed += 1
        invalidate_cache()
        return fixed

    @staticmethod
    def list_rules() -> List[Dict[str, str]]:
        return [{"merchant": k, "category": v} for k, v in sorted(Categorizer._load_rules().items())]

    @staticmethod
    def delete_rule(merchant: str) -> bool:
        with db.session() as session:
            deleted = session.query(UserPreference).filter(
                UserPreference.key == RULE_PREFIX + merchant
            ).delete()
        invalidate_cache()
        return bool(deleted)

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
        Reclassifica uma transação e aprende a regra do estabelecimento (usado pela CLI).

        Returns:
            bool: True se aprendeu com sucesso.
        """
        try:
            with db.session() as session:
                tx = session.get(Transaction, transaction_id)
                cat = session.query(Category).filter(Category.name == new_category_name).first()
                if not tx or not cat:
                    return False
                description, previous = tx.description, tx.category_name
                tx.category_id = cat.id
                tx.category_name = cat.name
            self.learn(description, cat.name, previous)
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

            invalidate_cache()
            return created
        except Exception:
            return 0
