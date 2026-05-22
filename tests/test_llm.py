"""Testes para o cliente LLM (E020-E025 da Matriz de Erros)."""

from unittest.mock import MagicMock, patch

import ollama
import pytest

from stonks_ai.llm.client import LLMError, OllamaClient


# ====== Testes OllamaClient ======

class TestOllamaClient:
    """Testes para E020-E025: Cliente Ollama."""

    def setup_method(self):
        self.client = OllamaClient(
            model="test-model",
            endpoint="http://localhost:11434",
            temperature=0.3,
            max_tokens=2048,
            timeout=30,
        )

    # ── Helpers ──────────────────────────────────────────────

    def _mock_client(self, mock_client_cls, list_retval=None, show_retval=None,
                     chat_retval=None, list_side_effect=None, show_side_effect=None,
                     chat_side_effect=None) -> MagicMock:
        """Configura um mock de ollama.Client com os retornos desejados."""
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance

        if list_side_effect:
            mock_instance.list.side_effect = list_side_effect
        else:
            mock_instance.list.return_value = list_retval or {"models": []}

        if show_side_effect:
            mock_instance.show.side_effect = show_side_effect
        else:
            mock_instance.show.return_value = show_retval or {"modelfile": ""}

        if chat_side_effect:
            mock_instance.chat.side_effect = chat_side_effect
        elif chat_retval is not None:
            mock_instance.chat.return_value = chat_retval

        return mock_instance

    # ── _check_ollama ────────────────────────────────────────

    @patch("ollama.Client")
    def test_check_ollama_success(self, mock_client_cls):
        """Testa verificacao bem-sucedida do Ollama."""
        self._mock_client(mock_client_cls)

        self.client._check_ollama()
        assert self.client._available is True

    @patch("ollama.Client")
    def test_ollama_not_running(self, mock_client_cls):
        """E020: Ollama nao esta rodando."""
        self._mock_client(mock_client_cls, list_side_effect=ConnectionError("Connection refused"))

        with pytest.raises(LLMError) as exc:
            self.client._check_ollama()
        assert "LLM-001" in str(exc.value)

    @patch("ollama.Client")
    def test_ollama_model_missing(self, mock_client_cls):
        """E021: Modelo nao encontrado."""
        self._mock_client(
            mock_client_cls,
            show_side_effect=ollama.ResponseError(
                '{"error": "model \'test-model\' not found"}', 404
            ),
        )

        with pytest.raises(LLMError) as exc:
            self.client._check_ollama()
        assert "LLM-002" in str(exc.value), (
            "Deveria retornar LLM-002 (modelo nao encontrado), "
            f"mas retornou {exc.value.code if hasattr(exc.value, 'code') else exc.value}"
        )

    # ── generate ─────────────────────────────────────────────

    @patch("ollama.Client")
    def test_generate_success(self, mock_client_cls):
        """Testa geracao de texto bem-sucedida."""
        self._mock_client(
            mock_client_cls,
            chat_retval={"message": {"content": "Analise: PETR4 e uma boa acao."}},
        )

        result = self.client.generate("Analise PETR4")
        assert "PETR4" in result
        assert self.client._available is True

    @patch("ollama.Client")
    def test_generate_with_system_prompt(self, mock_client_cls):
        """Testa geracao com system prompt."""
        mock_instance = self._mock_client(
            mock_client_cls,
            chat_retval={"message": {"content": "Resposta com contexto de sistema."}},
        )

        result = self.client.generate(
            "Prompt de teste",
            system_prompt="Voce e um analista.",
        )
        assert "Resposta" in result

        # Verifica que system prompt foi enviado via generate_from_messages
        # generate() constroi messages e chama generate_from_messages()
        # que cria ollama.Client e chama client.chat()
        call_args = mock_instance.chat.call_args
        messages = call_args[1]["messages"]
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    @patch("ollama.Client")
    def test_ollama_oom(self, mock_client_cls):
        """E022: GPU out of memory."""
        self._mock_client(
            mock_client_cls,
            chat_side_effect=ollama.ResponseError(
                '{"error": "out of memory error: CUDA out of memory"}', 500
            ),
        )

        with pytest.raises(LLMError) as exc:
            self.client.generate("Test prompt")
        assert "LLM-003" in str(exc.value)

    @patch("ollama.Client")
    def test_ollama_bad_response(self, mock_client_cls):
        """E023: Resposta mal formatada do modelo."""
        self._mock_client(
            mock_client_cls,
            chat_side_effect=ollama.ResponseError(
                '{"error": "invalid response format"}', 400
            ),
        )

        with pytest.raises(LLMError) as exc:
            self.client.generate("Test prompt")
        assert "LLM-004" in str(exc.value)

    @patch("ollama.Client")
    def test_ollama_context_overflow(self, mock_client_cls):
        """E024: Prompt muito longo."""
        self._mock_client(
            mock_client_cls,
            chat_side_effect=ollama.ResponseError(
                '{"error": "context length exceeded"}', 400
            ),
        )

        with pytest.raises(LLMError) as exc:
            self.client.generate("Very long prompt " * 10000)
        assert "LLM-004" in str(exc.value)

    @patch("ollama.Client")
    def test_ollama_inference_timeout(self, mock_client_cls):
        """E025: Timeout na inferencia."""
        self._mock_client(
            mock_client_cls,
            chat_side_effect=TimeoutError("Inference timed out"),
        )

        with pytest.raises(LLMError) as exc:
            self.client.generate("Test prompt")
        assert "LLM-006" in str(exc.value)

    # ── generate_from_messages ───────────────────────────────

    @patch("ollama.Client")
    def test_generate_from_messages(self, mock_client_cls):
        """Testa geracao a partir de lista de mensagens."""
        mock_instance = self._mock_client(
            mock_client_cls,
            chat_retval={"message": {"content": "Resposta com historico."}},
        )

        messages = [
            {"role": "user", "content": "Ola"},
            {"role": "assistant", "content": "Oi"},
            {"role": "user", "content": "Analise PETR4"},
        ]
        result = self.client.generate_from_messages(messages)

        assert "Resposta" in result

        # Verifica que todas as mensagens foram enviadas
        call_args = mock_instance.chat.call_args
        sent_messages = call_args[1]["messages"]
        assert len(sent_messages) == 3
        assert sent_messages[0]["role"] == "user"
        assert sent_messages[0]["content"] == "Ola"
        assert sent_messages[1]["role"] == "assistant"
        assert sent_messages[2]["role"] == "user"

    @patch("ollama.Client")
    def test_generate_from_messages_with_system_prompt(self, mock_client_cls):
        """Testa generate_from_messages com system_prompt adicional."""
        mock_instance = self._mock_client(
            mock_client_cls,
            chat_retval={"message": {"content": "Analise financeira."}},
        )

        messages = [{"role": "user", "content": "Analise PETR4"}]
        result = self.client.generate_from_messages(
            messages,
            system_prompt="Voce e um analista financeiro.",
        )

        assert "Analise" in result

        # System prompt deve ser inserido no inicio
        call_args = mock_instance.chat.call_args
        sent_messages = call_args[1]["messages"]
        assert sent_messages[0]["role"] == "system"
        assert "analista financeiro" in sent_messages[0]["content"]
        assert sent_messages[1]["role"] == "user"

    # ── is_available ─────────────────────────────────────────

    @patch("ollama.Client")
    def test_is_available_true(self, mock_client_cls):
        """Testa is_available retornando True."""
        self._mock_client(mock_client_cls)

        assert self.client.is_available() is True

    @patch("ollama.Client")
    def test_is_available_false(self, mock_client_cls):
        """Testa is_available retornando False quando Ollama nao responde."""
        self._mock_client(mock_client_cls, list_side_effect=ConnectionError())

        assert self.client.is_available() is False

    @patch("ollama.Client")
    def test_is_available_cached(self, mock_client_cls):
        """Testa que is_available usa cache _available."""
        # Primeira chamada: _check_ollama e chamado, define _available=True
        self._mock_client(mock_client_cls)
        assert self.client.is_available() is True

        # Segunda chamada: _available ja e True, retorna imediatamente sem chamar Client
        mock_client_cls.reset_mock()
        assert self.client.is_available() is True
        mock_client_cls.assert_not_called()

    # ── generate_structured ──────────────────────────────────

    @patch("ollama.Client")
    def test_generate_structured_json(self, mock_client_cls):
        """Testa geracao estruturada JSON."""
        self._mock_client(
            mock_client_cls,
            chat_retval={
                "message": {"content": '{"recommendation": "buy", "confidence": 0.85}'}
            },
        )

        result = self.client.generate_structured(
            "Analise PETR4",
            output_format="json",
        )
        assert "recommendation" in result

    # ── available_models ─────────────────────────────────────

    @patch("ollama.Client")
    def test_available_models(self, mock_client_cls):
        """Testa listagem de modelos disponiveis."""
        self._mock_client(
            mock_client_cls,
            list_retval={
                "models": [
                    {"name": "llama3.2:3b", "size": "2.0GB"},
                    {"name": "mistral:7b", "size": "4.1GB"},
                ]
            },
        )

        models = self.client.available_models
        assert len(models) == 2

    @patch("ollama.Client")
    def test_available_models_error(self, mock_client_cls):
        """Testa available_models quando Ollama nao responde."""
        self._mock_client(mock_client_cls, list_side_effect=Exception())

        models = self.client.available_models
        assert models == []

    # ── generate_stream ──────────────────────────────────────

    @patch("ollama.Client")
    @pytest.mark.asyncio
    async def test_generate_stream(self, mock_client_cls):
        """Testa geracao em streaming."""
        mock_instance = self._mock_client(mock_client_cls)

        # Simula chunks de streaming
        class MockStream:
            def __iter__(self):
                chunks = [
                    {"message": {"content": "A"}},
                    {"message": {"content": "nal"}},
                    {"message": {"content": "ise"}},
                ]
                return iter(chunks)

        mock_instance.chat.return_value = MockStream()

        result = ""
        async for chunk in self.client.generate_stream("Analise PETR4"):
            result += chunk

        assert result == "Analise"

    # ── LLMError ─────────────────────────────────────────────

    def test_llm_error_creation(self):
        """Testa criacao de LLMError."""
        error = LLMError("LLM-001", "Ollama nao esta rodando.")
        assert error.code == "LLM-001"
        assert "LLM-001" in str(error)
