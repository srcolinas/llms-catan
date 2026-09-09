import functools
import pathlib
from typing import Literal

import dotenv
import pydantic
import pydantic_settings


class Settings(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(
        env_file=".env",
        env_prefix="TEYUNA_",
        extra="ignore",
        frozen=True,
        populate_by_name=True,
    )

    loglevel: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    rulebook: pathlib.Path
    howto: pathlib.Path

    langfuse_public_key: pydantic.SecretStr = pydantic.Field(
        validation_alias=pydantic.AliasChoices("LANGFUSE_PUBLIC_KEY")
    )
    langfuse_secret_key: pydantic.SecretStr = pydantic.Field(
        validation_alias=pydantic.AliasChoices("LANGFUSE_SECRET_KEY")
    )
    langfuse_base_url: str = pydantic.Field(
        validation_alias=pydantic.AliasChoices("LANGFUSE_BASE_URL")
    )

    sleep_seconds: int = 2

    llm_model: str
    """pydantic-ai model id in `provider:model` form, e.g. `openai:gpt-4o`."""


@functools.cache
def settings() -> Settings:
    dotenv.load_dotenv()
    return Settings()
