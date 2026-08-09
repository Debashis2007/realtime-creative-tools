"""Mock LLM that streams fake tokens with configurable delay (no API keys)."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator


class MockLLM:
    def __init__(self, model: str = "mock-mid", tokens_per_sec: float = 40.0) -> None:
        self.model = model
        self.tokens_per_sec = tokens_per_sec

    async def complete(self, prompt: str, max_tokens: int = 32) -> str:
        parts: list[str] = []
        async for tok in self.stream(prompt, max_tokens=max_tokens):
            parts.append(tok)
        return "".join(parts)

    async def stream(self, prompt: str, max_tokens: int = 32) -> AsyncIterator[str]:
        # Tiny TTFT simulation
        await asyncio.sleep(0.05)
        words = self._fabricate(prompt, max_tokens)
        delay = 1.0 / max(self.tokens_per_sec, 1.0)
        for w in words:
            await asyncio.sleep(delay)
            yield w

    def _fabricate(self, prompt: str, max_tokens: int) -> list[str]:
        base = prompt.strip().split()[-8:] or ["hello"]
        seed = " ".join(base)
        text = (
            f"[{self.model}] Based on your prompt ({seed[:60]}…), "
            "here is a mock answer demonstrating streaming tokens. "
            "This is local POC output — no remote model was called."
        )
        tokens = text.split(" ")
        out: list[str] = []
        for i, t in enumerate(tokens[:max_tokens]):
            out.append(t if i == 0 else f" {t}")
        return out
