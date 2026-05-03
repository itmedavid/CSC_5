"""Factory for LLM providers. Reads `settings.LLM_PROVIDER` by default."""

from __future__ import annotations

from typing import Optional

import settings
from llm.base import LLMProvider


def get_provider(name: Optional[str] = None) -> LLMProvider:
    name = (name or settings.LLM_PROVIDER).strip().lower()
    if name == "mock":
        from llm.mock_provider import MockProvider
        return MockProvider()
    if name == "anthropic":
        from llm.anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    if name == "openai":
        from llm.openai_provider import OpenAIProvider
        return OpenAIProvider()
    raise ValueError(
        f"Unknown LLM provider: {name!r}. "
        "Set LLM_PROVIDER to one of: anthropic, openai, mock."
    )
