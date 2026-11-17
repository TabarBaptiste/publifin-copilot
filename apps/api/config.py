from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    ollama_base_url: str = "http://localhost:11434"
    ollama_embed_model: str = "bge-m3"
    corpus_dir: Path = REPO_ROOT / "data" / "corpus"
    vector_store_dir: Path = REPO_ROOT / "data" / "chroma"


settings = Settings()
