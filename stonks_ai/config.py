"""
Gerenciamento de configuração do Stonks AI.

Gerencia o arquivo config.yaml no diretório data/ com as preferências
do usuário, credenciais e configurações do sistema.
"""

import copy
import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


# Diretório base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# Diretório de dados (banco SQLite + config)
DATA_DIR = BASE_DIR / "data"

# Caminhos padrão
DEFAULT_CONFIG_PATH = DATA_DIR / "config.yaml"
DEFAULT_DB_PATH = DATA_DIR / "stonks_ai.db"

# Configuração padrão
DEFAULT_CONFIG: Dict[str, Any] = {
    "app": {
        "name": "Stonks AI",
        "version": "0.1.0",
        "language": "pt-BR",
        "currency": "BRL",
    },
    "database": {
        "path": str(DEFAULT_DB_PATH),
    },
    "stocks": {
        "default_exchange": "B3",
        "b3_suffix": ".SA",
        "cache_ttl_minutes": 5,
    },
    "llm": {
        "provider": "ollama",
        "model": "llama3.2:3b",
        "endpoint": "http://localhost:11434",
        "temperature": 0.3,
        "max_tokens": 2048,
        "timeout_seconds": 120,
    },
    "finance": {
        "default_currency": "BRL",
        "alert_interval_hours": 24,
        "dashboard_days_history": 90,
        "import_default_source": "manual",
    },
    "ui": {
        "theme": "default",
        "show_color": True,
        "chart_width": 60,
        "chart_height": 15,
    },
}


class ConfigError(Exception):
    """Erro relacionado à configuração do sistema."""

    pass


class Config:
    """Gerenciador de configuração do Stonks AI."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self._data: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Carrega a configuração do arquivo YAML ou cria padrão."""
        if not self.config_path.exists():
            self._create_default()
        else:
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f) or {}
                    # Merge com defaults para garantir chaves novas
                    self._data = self._deep_merge(DEFAULT_CONFIG.copy(), loaded)
            except yaml.YAMLError as e:
                raise ConfigError(
                    f"CFG-001: Arquivo de configuração inválido. "
                    f"Verifique a sintaxe YAML em {self.config_path}. Erro: {e}"
                )

    def _create_default(self) -> None:
        """Cria arquivo de configuração padrão."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._data = copy.deepcopy(DEFAULT_CONFIG)
        self.save()

    def save(self) -> None:
        """Salva a configuração atual no arquivo YAML."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(self._data, f, default_flow_style=False, allow_unicode=True)

    @staticmethod
    def _deep_merge(base: Dict, override: Dict) -> Dict:
        """Mescla profundamente dois dicionários."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = Config._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Obtém um valor da configuração por chaves aninhadas.

        Exemplo: config.get("llm", "model") -> "llama3.2:3b"
        """
        current = self._data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
                if current is None:
                    return default
            else:
                return default
        return current

    def set(self, value: Any, *keys: str) -> None:
        """
        Define um valor na configuração por chaves aninhadas.

        Exemplo: config.set("llama3.2:3b", "llm", "model")
        """
        current = self._data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
        self.save()

    @property
    def data(self) -> Dict[str, Any]:
        """Retorna o dicionário completo de configuração."""
        return self._data

    @property
    def db_path(self) -> Path:
        """Caminho completo do arquivo do banco SQLite."""
        path = self.get("database", "path", default=str(DEFAULT_DB_PATH))
        p = Path(path)
        if not p.is_absolute():
            p = BASE_DIR / p
        return p.resolve()

    @property
    def llm_model(self) -> str:
        """Nome do modelo LLM configurado."""
        return self.get("llm", "model", default="llama3.2:3b")

    @property
    def llm_endpoint(self) -> str:
        """Endpoint do serviço Ollama."""
        return self.get("llm", "endpoint", default="http://localhost:11434")


# Singleton global
config = Config()
