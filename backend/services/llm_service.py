from abc import ABC, abstractmethod
from typing import Dict, Any
from backend.core.config import get_settings


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate(self, system_prompt: str, user_message: str) -> str:
        pass

    @abstractmethod
    def get_provider_info(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass


class OllamaProvider(BaseLLMProvider):
    """Local Ollama LLM provider (mistral / llama3.2)."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral"):
        self.base_url = base_url
        self.model = model
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            from langchain_ollama import ChatOllama
            self._llm = ChatOllama(
                base_url=self.base_url,
                model=self.model,
                temperature=0.1,  # Strict factual grounding for agronomy
            )
        return self._llm

    def is_available(self) -> bool:
        try:
            import httpx
            r = httpx.get(f"{self.base_url}/api/tags", timeout=2.0)
            return r.status_code == 200
        except Exception:
            return False

    async def generate(self, system_prompt: str, user_message: str) -> str:
        from langchain_core.messages import SystemMessage, HumanMessage
        llm = self._get_llm()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        response = await llm.ainvoke(messages)
        return response.content

    def get_provider_info(self) -> Dict[str, Any]:
        return {
            "provider": "ollama",
            "model": self.model,
            "base_url": self.base_url,
            "available": self.is_available(),
        }


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek Cloud LLM provider (inactive stub if no API key set)."""

    def __init__(self, api_key: str = "", model: str = "deepseek-chat"):
        self.api_key = api_key
        self.model = model

    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 5)

    async def generate(self, system_prompt: str, user_message: str) -> str:
        if not self.is_available():
            raise ValueError(
                "DeepSeek API key not configured. Set DEEPSEEK_API_KEY in .env or switch to Ollama."
            )
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage

        llm = ChatOpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com/v1",
            model=self.model,
            temperature=0.1,
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        response = await llm.ainvoke(messages)
        return response.content

    def get_provider_info(self) -> Dict[str, Any]:
        return {
            "provider": "deepseek",
            "model": self.model,
            "available": self.is_available(),
        }


class LLMService:
    def __init__(self):
        settings = get_settings()
        self.settings = settings
        if settings.LLM_PROVIDER == "deepseek":
            self.provider = DeepSeekProvider(api_key=settings.DEEPSEEK_API_KEY, model=settings.DEEPSEEK_MODEL)
        else:
            self.provider = OllamaProvider(base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL)

    async def generate_response(self, system_prompt: str, user_message: str) -> str:
        return await self.provider.generate(system_prompt, user_message)

    def get_info(self) -> Dict[str, Any]:
        return self.provider.get_provider_info()
