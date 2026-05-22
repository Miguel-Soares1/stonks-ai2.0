"""Testes unitários para o módulo de configuração."""

import json
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from stonks_ai.config import Config, ConfigError, DEFAULT_CONFIG


class TestConfig:
    """Testes para gerenciamento de configuração."""

    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)

    def test_create_default_config(self, temp_dir):
        """Testa criação de config padrão quando arquivo não existe."""
        config_path = temp_dir / "config.yaml"
        cfg = Config(config_path)
        assert config_path.exists()
        assert cfg.get("app", "name") == "Stonks AI"
        assert cfg.get("llm", "model") == "llama3.2:3b"

    def test_load_existing_config(self, temp_dir):
        """Testa carregamento de config existente."""
        config_path = temp_dir / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump({"app": {"name": "Stonks Test"}}, f)

        cfg = Config(config_path)
        assert cfg.get("app", "name") == "Stonks Test"
        # Valores padrão devem ser preservados
        assert cfg.get("llm", "model") == "llama3.2:3b"

    def test_invalid_yaml(self, temp_dir):
        """E029: Config YAML inválido."""
        config_path = temp_dir / "config.yaml"
        with open(config_path, "w") as f:
            f.write("invalid: yaml: : : broken")

        with pytest.raises(ConfigError) as exc:
            Config(config_path)
        assert "CFG-001" in str(exc.value)

    def test_set_and_get(self, temp_dir):
        """Testa definir e obter valores na config."""
        config_path = temp_dir / "config.yaml"
        cfg = Config(config_path)
        cfg.set("test-model", "llm", "model")
        assert cfg.get("llm", "model") == "test-model"

        # Verifica que foi salvo no arquivo
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["llm"]["model"] == "test-model"

    def test_get_nested_default(self, temp_dir):
        """Testa valor default para chave inexistente."""
        cfg = Config(temp_dir / "config.yaml")
        assert cfg.get("nonexistent", "key", default=42) == 42

    def test_properties(self, temp_dir):
        """Testa propriedades de conveniência."""
        cfg = Config(temp_dir / "config.yaml")
        assert cfg.llm_model == "llama3.2:3b"
        assert "stonks_ai.db" in str(cfg.db_path)
