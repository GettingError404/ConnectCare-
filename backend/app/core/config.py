from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENV: str = "development"

    DATABASE_URL: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/connectedcare"
    )

    REDIS_URL: str | None = None

    # pgvector
    PGVECTOR_EMBEDDING_DIMENSION: int = Field(default=1536, gt=0)
    PGVECTOR_IVFFLAT_LISTS: int = Field(default=100, gt=0)
    PGVECTOR_IVFFLAT_PROBES: int = Field(default=10, gt=0)

    # Embedding providers
    EMBEDDING_PROVIDER: str = "mock"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Embedding runtime
    EMBEDDING_MAX_TEXT_LENGTH: int = Field(default=50000, gt=0)
    EMBEDDING_CHUNK_SIZE_TOKENS: int = Field(default=400, gt=0)
    EMBEDDING_CHUNK_OVERLAP_TOKENS: int = Field(default=40, ge=0)
    EMBEDDING_PROVIDER_TIMEOUT_SECONDS: float = Field(default=20.0, gt=0)
    EMBEDDING_MAX_RETRIES: int = Field(default=3, ge=0)
    EMBEDDING_RETRY_BACKOFF_SECONDS: float = Field(default=0.5, gt=0)

    # Embedding cache
    EMBEDDING_CACHE_TTL_SECONDS: int = Field(default=86400, gt=0)
    EMBEDDING_CACHE_PREFIX: str = "cc:emb"

    # AI memory intelligence
    AI_MEMORY_DECAY_RATE: float = Field(default=0.001, ge=0.0, le=1.0)
    AI_MEMORY_RETENTION_SHORT_DAYS: int = Field(default=30, ge=1)
    AI_MEMORY_RETENTION_EPISODIC_DAYS: int = Field(default=180, ge=1)
    AI_MEMORY_RETENTION_LONG_DAYS: int = Field(default=730, ge=1)
    AI_MEMORY_RETRIEVAL_CACHE_TTL_SECONDS: int = Field(default=120, ge=1)
    AI_MEMORY_RETRIEVAL_CACHE_PREFIX: str = "cc:aimemory:retrieval"

    # Celery
    USE_CELERY: bool = False

    # MQTT
    ENABLE_MQTT: bool = False
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_CLIENT_ID: str | None = None
    MQTT_USERNAME: str | None = None
    MQTT_PASSWORD: str | None = None

    # JWT
    SECRET_KEY: str = "changeme-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()