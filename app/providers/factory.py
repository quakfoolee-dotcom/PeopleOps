from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.providers.adapters import (
    DeterministicProvider,
    DisabledProvider,
    MisconfiguredProvider,
    OpenAICompatibleProvider,
)
from app.providers.contracts import LLMProvider

DISABLED_PROVIDER_NAMES = frozenset({"", "none", "disabled", "not-configured"})


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    provider_name = settings.llm_provider.casefold().strip()
    if provider_name in DISABLED_PROVIDER_NAMES:
        return DisabledProvider()
    if provider_name == "deterministic":
        return DeterministicProvider()
    if provider_name not in {"openrouter", "openai-compatible"}:
        return MisconfiguredProvider(
            provider_name,
            settings.llm_model,
            f"Unsupported LLM provider {provider_name!r}.",
        )
    if settings.llm_model.casefold() in DISABLED_PROVIDER_NAMES:
        return MisconfiguredProvider(
            provider_name,
            settings.llm_model,
            "LLM_MODEL must name a model when an external provider is enabled.",
        )
    if settings.llm_api_key is None:
        return MisconfiguredProvider(
            provider_name,
            settings.llm_model,
            "LLM_API_KEY or OPENROUTER_API_KEY is required for the configured provider.",
        )
    return OpenAICompatibleProvider(
        name=provider_name,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key.get_secret_value(),
        timeout_seconds=settings.llm_timeout_seconds,
        max_output_tokens=settings.llm_max_output_tokens,
        temperature=settings.llm_temperature,
        health_cache_seconds=settings.llm_health_cache_seconds,
        http_referer=settings.llm_http_referer,
        app_title=settings.llm_app_title,
    )
