from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List, Union
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./crophealth.db"

    # API Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    ALLOWED_ORIGINS: Union[List[str], str] = ["http://localhost:5173", "http://localhost:3000"]
    DEBUG: bool = True

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            if v.startswith("["):
                return json.loads(v)
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

    # LLM Settings
    LLM_PROVIDER: str = "ollama"  # "ollama" | "deepseek"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "mistral"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # Embeddings & RAG
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_PROVIDER: str = "huggingface"
    CHROMA_PERSIST_PATH: str = "./chroma_db"

    # Computer Vision
    CV_CONFIDENCE_THRESHOLD: float = 0.65

    # File Storage & Crops Path
    CROPS_DIRECTORY: str = "./crops"
    UPLOADS_DIR: str = "./uploads"
    MAX_IMAGE_SIZE_MB: int = 10

    # Simulation Mode
    SIMULATION_MODE: bool = True
    LOG_LEVEL: str = "INFO"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
