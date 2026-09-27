from abc import ABC, abstractmethod
from pydantic import BaseModel, Field

class AgentPrompt(BaseModel):
    system_prompt: str
    user_prompt: str
    context_data: dict = Field(default_factory=dict)
    temperature: float = 0.2

class AgentResponse(BaseModel):
    raw_text: str
    structured_output: dict = Field(default_factory=dict)
    model_name: str
    tokens_used: int = 0
    latency_ms: int = 0

class BaseAgentReasoner(ABC):
    """
    Contract for Autonomous Reasoning Agents (e.g. Qwen2.5-Coder 7B via Ollama).
    LLM reasoning is used as a deliberate reasoning component, not the entire platform.
    """
    @abstractmethod
    async def reason(self, prompt: AgentPrompt) -> AgentResponse:
        """Execute reasoning step against local LLM endpoint."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify local LLM runner connectivity."""
        pass
