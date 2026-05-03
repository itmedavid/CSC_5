"""LLM provider contract.

All providers expose the same `complete(system, user, ...)` interface and
return an `LLMResponse` with usage and metadata fields populated. The
formatter calls only this interface — never an SDK directly — so providers
are swappable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    latency_ms: int = 0
    raw: Any = field(default=None, repr=False)

    def usage_dict(self) -> dict[str, int]:
        return {
            "input": self.input_tokens,
            "output": self.output_tokens,
            "cache_read": self.cache_read_tokens,
            "cache_write": self.cache_write_tokens,
        }


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 800,
        temperature: float = 0.2,
        cache_system: bool = True,
    ) -> LLMResponse: ...
