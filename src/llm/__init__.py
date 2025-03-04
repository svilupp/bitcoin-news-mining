"""LLM utilities package for async OpenAI operations."""

from openai import AsyncOpenAI
from typing import Optional, Dict, Any, Literal

# Default base URLs for different providers
PROVIDER_URLS = {
    "openai": None,  # Default OpenAI API URL
    "google": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
    "anthropic": "https://api.anthropic.com/v1",
    "azure": None,  # Requires specific deployment info
}

# Default model names by provider
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "google": "gemini-1.5-pro",
    "anthropic": "claude-3-haiku-20240307",
    "azure": "gpt-4",
}


def create_async_client(
    api_key: Optional[str] = None,
    provider: Literal["openai", "google", "anthropic", "azure"] = "openai",
    base_url: Optional[str] = None,
    **kwargs: Any,
) -> AsyncOpenAI:
    """Create an async OpenAI client configured for different providers.

    Args:
        api_key: API key for the provider (if None, will use environment variable)
        provider: The API provider to use (openai, google, anthropic, azure)
        base_url: Optional base URL for the API (overrides provider default)
        **kwargs: Additional arguments to pass to AsyncOpenAI constructor

    Returns:
        AsyncOpenAI client instance configured for the specified provider
    """
    # If base_url not specified, use the provider default
    if base_url is None and provider in PROVIDER_URLS:
        base_url = PROVIDER_URLS[provider]

    # Create the client with the specified configuration
    return AsyncOpenAI(api_key=api_key, base_url=base_url, **kwargs)


def get_default_model(
    provider: Literal["openai", "google", "anthropic", "azure"] = "openai"
) -> str:
    """Get the default model name for a provider.

    Args:
        provider: The API provider

    Returns:
        Default model name for the provider
    """
    return DEFAULT_MODELS.get(provider, DEFAULT_MODELS["openai"])
