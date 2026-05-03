"""Anthropic provider — primary path with prompt caching on the system block.

The system prompt is large and stable across notes within a session, so
`cache_control={"type": "ephemeral"}` is set on the system block. After the
first note in a session, subsequent notes serve the cached system prefix at
~0.1× input cost.

Note: caching only triggers for prefixes ≥ ~2K tokens (Sonnet 4.6) or 4K
(Opus 4.7). The header is harmless if the prefix is below the minimum.

Model differences:
- Opus 4.7 removed `temperature`, `top_p`, `top_k` (400 if sent). We omit
  `temperature` for `claude-opus-4-*` IDs.
"""

from __future__ import annotations

import time

import settings
from llm.base import LLMProvider, LLMResponse


def _is_opus_4_x(model: str) -> bool:
    return model.startswith("claude-opus-4")


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self) -> None:
        try:
            import anthropic  # noqa: F401
        except ImportError as e:
            raise RuntimeError(
                "anthropic SDK not installed. Run `pip install anthropic`."
            ) from e
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to crm_agent/.env."
            )

        from anthropic import Anthropic
        self._client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = settings.ANTHROPIC_MODEL

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 800,
        temperature: float = 0.2,
        cache_system: bool = True,
    ) -> LLMResponse:
        kwargs = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": user}],
        }

        if cache_system:
            kwargs["system"] = [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        else:
            kwargs["system"] = system

        if not _is_opus_4_x(self._model):
            kwargs["temperature"] = temperature

        start = time.perf_counter()
        response = self._client.messages.create(**kwargs)
        latency_ms = int((time.perf_counter() - start) * 1000)

        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        ).strip()

        usage = response.usage
        return LLMResponse(
            text=text,
            model=response.model,
            provider=self.name,
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
            cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            cache_write_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            latency_ms=latency_ms,
            raw=response,
        )
