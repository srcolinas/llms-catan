import functools
import pathlib
from typing import Literal, Self

import pydantic
import pydantic_settings
from pydantic_ai import models
from pydantic_ai.models import anthropic, bedrock, ollama, openai
from pydantic_ai.providers import anthropic as anthropic_providers
from pydantic_ai.providers import ollama as ollama_providers
from pydantic_ai.providers import openai as openai_providers


class Settings(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(
        env_file=".env",
        env_prefix="TEYUNA_",
        extra="ignore",
    )

    loglevel: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    rulebook: pathlib.Path
    howto: pathlib.Path

    sleep_seconds: int = 2

    openai_api_key: pydantic.SecretStr | None = None
    openai_model_id: str = "gpt-4o"

    anthropic_api_key: pydantic.SecretStr | None = None
    anthropic_model_id: str = "claude-sonnet-4-5"

    bedrock_model_id: str | None = None

    ollama_model_id: str | None = None
    ollama_base_url: str | None = None

    _model: models.Model | None = None

    @pydantic.model_validator(mode="after")
    def at_least_one_llm_provider(self) -> Self:
        if any(
            (
                self.openai_api_key,
                self.anthropic_api_key,
                self.bedrock_model_id,
                self.ollama_model_id,
            )
        ):
            return self
        raise ValueError(
            "No LLM provider configured: set one of TEYUNA_OPENAI_API_KEY, "
            "TEYUNA_ANTHROPIC_API_KEY, TEYUNA_BEDROCK_MODEL_ID, or "
            "TEYUNA_OLLAMA_MODEL_ID"
        )

    @property
    def llm_model(self) -> models.Model:
        model: models.Model | None = None
        if self.openai_api_key is not None:
            model = openai.OpenAIChatModel(
                self.openai_model_id,
                provider=openai_providers.OpenAIProvider(
                    api_key=self.openai_api_key.get_secret_value()
                ),
            )
        if self.anthropic_api_key is not None:
            model = anthropic.AnthropicModel(
                self.anthropic_model_id,
                provider=anthropic_providers.AnthropicProvider(
                    api_key=self.anthropic_api_key.get_secret_value()
                ),
            )
        if self.bedrock_model_id is not None:
            model = bedrock.BedrockConverseModel(self.bedrock_model_id)
        if self.ollama_model_id is not None:
            model = ollama.OllamaModel(
                self.ollama_model_id,
                provider=ollama_providers.OllamaProvider(
                    base_url=self.ollama_base_url
                ),
            )
        if model is None:
            raise RuntimeError("No LLM model configured")
        return model


@functools.cache
def settings() -> Settings:
    return Settings()
