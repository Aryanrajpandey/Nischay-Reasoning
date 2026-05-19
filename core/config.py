import json
import secrets
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    SECRET_KEY: str = "change-me-minimum-32-characters-long"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database
    DATABASE_URL: str = "sqlite:///./nischay.db"

    # AI
    GROQ_API_KEY: str = ""
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Database (Supabase optional)
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # Cache
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL_SECONDS: int = 3600

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:8000", "http://localhost:8501"]

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 30

    # HuggingFace
    HUGGINGFACE_TOKEN: str = ""

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        """Handle ALLOWED_ORIGINS as either a JSON string or a list."""
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
            # Treat as comma-separated if not valid JSON
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


def validate_settings(s: "Settings") -> None:
    """Fail fast if critical environment variables are invalid."""
    errors = []

    if s.SECRET_KEY in ("change-me-minimum-32-characters-long", ""):
        errors.append(
            "SECRET_KEY is still the default placeholder. "
            "Set a cryptographically random secret (min 32 chars)."
        )

    if len(s.SECRET_KEY) < 32:
        errors.append(
            f"SECRET_KEY is only {len(s.SECRET_KEY)} chars — minimum 32 required."
        )

    if s.ENVIRONMENT == "production" and s.DEBUG:
        errors.append(
            "DEBUG=True in production. Set DEBUG=False or ENVIRONMENT=development."
        )

    if not s.GROQ_API_KEY:
        errors.append(
            "GROQ_API_KEY is not set. The LLM chat pipeline requires a valid Groq API key."
        )

    if errors:
        raise RuntimeError(
            "Environment validation failed:\n" + "\n".join(f"  • {e}" for e in errors)
        )


settings = Settings()
validate_settings(settings)
