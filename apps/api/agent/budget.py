"""Limits of one analysis: token budget and time. The graph caps the number of steps."""

import time

from config import settings
from providers.base import LLMProvider


class BudgetExceeded(Exception):
    """The analysis used more tokens or time than allowed."""


class RunBudget:
    def __init__(self, max_tokens: int | None = None, timeout_seconds: float | None = None) -> None:
        self.max_tokens = max_tokens or settings.agent_max_tokens
        self.timeout_seconds = timeout_seconds or settings.agent_timeout_seconds
        self.tokens = 0
        self.started = time.monotonic()

    def spend(self, text: str) -> None:
        self.tokens += round(len(text) / 3.5)

    def check(self) -> None:
        if self.tokens > self.max_tokens:
            raise BudgetExceeded(f"Budget de {self.max_tokens} tokens dépassé ({self.tokens}).")
        if time.monotonic() - self.started > self.timeout_seconds:
            raise BudgetExceeded(f"Durée maximale de {self.timeout_seconds:.0f} s dépassée.")


class BudgetedProvider:
    """Wraps an LLM provider so that every call is counted against the run budget."""

    def __init__(self, provider: LLMProvider, budget: RunBudget) -> None:
        self._provider = provider
        self.budget = budget

    def chat(self, messages: list[dict[str, str]], json_schema: dict | None = None) -> str:
        self.budget.check()
        self.budget.spend("".join(m["content"] for m in messages))
        reply = self._provider.chat(messages, json_schema)
        self.budget.spend(reply)
        self.budget.check()
        return reply

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.budget.check()
        return self._provider.embed(texts)

    def warm_up(self) -> None:
        self._provider.warm_up()
