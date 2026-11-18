from typing import Protocol


class ProviderUnavailable(Exception):
    """The LLM server cannot be reached or returned an error."""


class LLMProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        """One embedding vector per text."""
        ...

    def chat(self, messages: list[dict[str, str]]) -> str:
        """Answer to a list of {"role", "content"} messages."""
        ...

    def warm_up(self) -> None:
        """Load the models in memory so the first question is not slowed down."""
        ...
