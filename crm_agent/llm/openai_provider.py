"""OpenAI provider — parity adapter (no prompt caching benefit).

Same `complete(system, user, ...)` interface as the Anthropic provider so the
formatter doesn't need to know which is in use.
"""

from __future__ import annotations

import time

import settings
from llm.base import LLMProvider, LLMResponse


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self) -> None:
        try:
            import openai  # noqa: F401
        except ImportError as e:
            raise RuntimeError(
                "openai SDK not installed. Run `pip install openai`."
            ) from e
        if not settings.OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to crm_agent/.env."
            )

        from openai import OpenAI
        self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.OPENAI_MODEL

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 800,
        temperature: float = 0.2,
        cache_system: bool = True,
    ) -> LLMResponse:
        start = time.perf_counter()
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        latency_ms = int((time.perf_counter() - start) * 1000)

        text = (response.choices[0].message.content or "").strip()
        usage = response.usage

        return LLMResponse(
            text=text,
            model=response.model,
            provider=self.name,
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            cache_read_tokens=0,
            cache_write_tokens=0,
            latency_ms=latency_ms,
            raw=response,
        )
