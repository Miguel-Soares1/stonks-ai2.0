"""Classe base para agentes de IA do Stonks AI."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from stonks_ai.database import DatabaseError, db
from stonks_ai.llm.client import LLMError, OllamaClient
from stonks_ai.llm.prompts import FINANCIAL_CHAT_SYSTEM_PROMPT


class AgentError(Exception):
    """Erro base para agentes."""
    pass


class BaseAgent(ABC):
    """Classe base abstrata para todos os agentes de IA."""

    def __init__(self, llm_client: Optional[OllamaClient] = None):
        self.llm = llm_client or OllamaClient()
        self._name = self.__class__.__name__

    def execute(self, *args, **kwargs) -> Any:
        """Executa a tarefa principal do agente.
        
        Pode ser sobrescrito por subclasses específicas.
        Por padrão, retorna uma mensagem indicando que não há tarefa definida.
        """
        return {"message": f"{self._name}: Nenhuma tarefa padrão definida."}

    def save_to_history(self, model: Any) -> None:
        """Salva registro no histórico do banco de dados."""
        try:
            with db.session() as session:
                session.add(model)
        except DatabaseError as e:
            raise AgentError(f"Erro ao salvar histórico: {e}")

    def check_llm_available(self) -> bool:
        """Verifica se o modelo LLM está disponível."""
        return self.llm.is_available()

    def get_llm_analysis(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Obtém análise do modelo LLM local."""
        try:
            return self.llm.generate(prompt, system_prompt=system_prompt)
        except LLMError as e:
            raise AgentError(f"Erro na análise IA: {e}")

    def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Envia uma mensagem para o chat financeiro e obtém resposta do modelo IA.

        Args:
            message: Mensagem do usuário sobre finanças/investimentos.
            conversation_history: Histórico da conversa no formato
                [{"role": "user"|"assistant", "content": "..."}].

        Returns:
            str: Resposta gerada pela IA.
        """
        if not self.check_llm_available():
            return (
                "⚠️ IA local não disponível. Certifique-se de que o Ollama "
                "está rodando (execute 'ollama serve' no terminal) e que "
                "o modelo foi baixado (ex: ollama pull llama3.2:3b)."
            )

        try:
            messages = []
            if conversation_history:
                messages.extend(conversation_history)
            messages.append({"role": "user", "content": message})

            response = self.llm.generate_from_messages(
                messages=messages,
                system_prompt=FINANCIAL_CHAT_SYSTEM_PROMPT,
            )
            return response
        except LLMError as e:
            raise AgentError(f"Erro no chat: {e}")
        except Exception as e:
            raise AgentError(f"Erro inesperado no chat: {e}")
