from pathlib import Path

from pydantic_settings import BaseSettings

# Resolve .env relative to Backend/ directory
_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class OpenRouterConfig(BaseSettings):
    """LLM provider configuration. Supports Groq, NVIDIA NIM, and OpenRouter."""

    # Provider: "groq", "nvidia", or "openrouter"
    llm_provider: str = "groq"

    # Groq settings
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # NVIDIA NIM settings
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "meta/llama-3.1-70b-instruct"

    # OpenRouter settings
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "qwen/qwen3-235b-a22b:free"

    @property
    def api_key(self) -> str:
        if self.llm_provider == "groq":
            return self.groq_api_key
        if self.llm_provider == "nvidia":
            return self.nvidia_api_key
        return self.openrouter_api_key

    @property
    def base_url(self) -> str:
        if self.llm_provider == "groq":
            return "https://api.groq.com/openai/v1"
        if self.llm_provider == "nvidia":
            return self.nvidia_base_url
        return self.openrouter_base_url

    @property
    def default_model(self) -> str:
        if self.llm_provider == "groq":
            return self.groq_model
        if self.llm_provider == "nvidia":
            return self.nvidia_model
        return self.openrouter_model

    class Config:
        env_file = str(_ENV_FILE)
        extra = "ignore"
