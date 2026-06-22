from control.config.openrouter_config import OpenRouterConfig
from langchain_openai import ChatOpenAI


class LLMFactory:
    @staticmethod
    def get_llm(temperature: float = 0.3):
        config = OpenRouterConfig()

        return ChatOpenAI(
            model=config.default_model,
            api_key=config.api_key,
            base_url=config.base_url,
            temperature=temperature,
            max_tokens=1024,
            timeout=60,
            max_retries=2,
        )
