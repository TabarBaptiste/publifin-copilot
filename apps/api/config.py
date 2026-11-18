from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    # "ollama" (local) or "azure_openai" (cloud, Entra ID authentication, no key).
    llm_provider: str = "ollama"
    # "chroma" (local files) or "azure_search". Left empty: follows llm_provider, because
    # embeddings from different models are not comparable and need their own index.
    vector_store: str = ""

    azure_openai_endpoint: str = ""
    azure_openai_chat_deployment: str = "chat"
    azure_openai_embed_deployment: str = "embeddings"
    azure_openai_api_version: str = "2024-10-21"
    azure_search_endpoint: str = ""
    azure_search_index: str = "corpus"
    embedding_dimensions: int = 1536  # text-embedding-3-small

    ollama_base_url: str = "http://localhost:11434"
    ollama_embed_model: str = "bge-m3"
    ollama_chat_model: str = "qwen3:4b-instruct"
    chat_context_tokens: int = 8192
    chat_timeout_seconds: float = 180
    # How long Ollama keeps a model in memory after a request (its default is 5 minutes).
    # Both models together use about 4.5 GB of RAM.
    ollama_keep_alive: str = "30m"

    corpus_dir: Path = REPO_ROOT / "data" / "corpus"
    vector_store_dir: Path = REPO_ROOT / "data" / "chroma"

    cors_origins: list[str] = ["http://localhost:3000"]

    top_k: int = 2
    # Passages farther than this (cosine distance) are considered unrelated to the question.
    max_distance: float = 0.43


settings = Settings()
