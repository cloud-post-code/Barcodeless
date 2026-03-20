from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/barcodeless"
    # None = infer from DATABASE_URL sslmode= / PGSSLMODE, or set True for Railway if URL has no sslmode
    database_ssl: bool | None = None
    clip_model: str = "ViT-L-14"
    clip_pretrained: str = "openai"
    embedding_dim: int = 768
    duplicate_threshold: float = 0.92
    top_k_recall: int = 50
    port: int = 8000

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://") and "+asyncpg" not in v:
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
