from config import settings
from providers.ollama import OllamaProvider


def capture_calls(monkeypatch):
    calls = []

    def fake_post(self, path, payload, timeout):
        calls.append((path, payload))
        return {"embeddings": [[0.0]], "message": {"content": "ok"}}

    monkeypatch.setattr(OllamaProvider, "_post", fake_post)
    return calls


def test_every_call_asks_ollama_to_keep_the_model_loaded(monkeypatch):
    calls = capture_calls(monkeypatch)
    provider = OllamaProvider()

    provider.embed(["a"])
    provider.chat([{"role": "user", "content": "q"}])

    assert all(payload["keep_alive"] == settings.ollama_keep_alive for _, payload in calls)


def test_warm_up_loads_chat_model_with_the_same_context_size_as_chat(monkeypatch):
    calls = capture_calls(monkeypatch)

    OllamaProvider().warm_up()

    generate = next(payload for path, payload in calls if path == "/api/generate")
    assert generate["model"] == settings.ollama_chat_model
    assert generate["options"]["num_ctx"] == settings.chat_context_tokens
    assert any(path == "/api/embed" for path, _ in calls)
