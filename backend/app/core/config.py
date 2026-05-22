from pydantic import Field, model_validator
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
    CORS_ALLOW_ORIGINS: str = ""
    TRUSTED_HOSTS: str = "localhost,127.0.0.1,0.0.0.0,[::1],testserver"
    MAX_REQUEST_BODY_BYTES: int = Field(default=1048576, ge=1024)

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

    # Rate limiting and auth hardening
    LOGIN_RATE_LIMIT_ATTEMPTS: int = Field(default=8, ge=1)
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60, ge=1)
    LOGIN_LOCKOUT_SECONDS: int = Field(default=300, ge=1)

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
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Observability
    SENTRY_DSN: str | None = None
    OTEL_SERVICE_NAME: str = "connectedcare-backend"
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None
    OTEL_TRACES_SAMPLE_RATIO: float = Field(default=0.0, ge=0.0, le=1.0)

    # Database pool tuning
    DATABASE_POOL_SIZE: int = Field(default=10, ge=1)
    DATABASE_MAX_OVERFLOW: int = Field(default=20, ge=0)
    DATABASE_POOL_RECYCLE_SECONDS: int = Field(default=1800, ge=1)
    DATABASE_POOL_TIMEOUT_SECONDS: int = Field(default=30, ge=1)

    @model_validator(mode="after")
    def validate_production_secrets(self):
        if self.ENV.lower() in {"production", "prod"}:
            if self.SECRET_KEY == "changeme-in-production" or len(self.SECRET_KEY) < 32:
                raise ValueError("SECRET_KEY must be set to a strong value in production")
            if self.ALGORITHM not in {"HS256", "HS384", "HS512"}:
                raise ValueError("ALGORITHM must be a supported HMAC JWT algorithm in production")
            trusted_hosts = [host.strip() for host in self.TRUSTED_HOSTS.split(",") if host.strip()]
            if not trusted_hosts:
                raise ValueError("TRUSTED_HOSTS must be configured in production")
            if "*" in trusted_hosts:
                raise ValueError("TRUSTED_HOSTS must not allow wildcard hosts in production")
            if self.MAX_REQUEST_BODY_BYTES <= 0:
                raise ValueError("MAX_REQUEST_BODY_BYTES must be positive in production")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()