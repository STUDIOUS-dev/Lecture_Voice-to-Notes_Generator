"""
Application configuration, read from environment variables.

Every setting has a sensible default so the app runs locally with zero
configuration. In production, set them in your host's dashboard or a `.env`
file (see `.env.example`).
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader (no extra dependency). Existing env vars win."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv(PROJECT_ROOT / ".env")


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


def _env_list(name: str, default: str) -> list[str]:
    return [item.strip() for item in _env(name, default).split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    # ── AI provider ────────────────────────────────────────────────────────
    # "auto"  -> use the hosted API when an API key is set, else local models
    # "api"   -> always use the hosted (OpenAI-compatible) API
    # "local" -> always use local Whisper / BART / Flan-T5 models
    ai_provider: str = field(default_factory=lambda: _env("AI_PROVIDER", "auto").lower())

    # Any OpenAI-compatible API works. Defaults target Groq (free tier).
    api_key: str = field(default_factory=lambda: _env("GROQ_API_KEY") or _env("LLM_API_KEY"))
    api_base_url: str = field(
        default_factory=lambda: _env("LLM_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
    )
    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL", "openai/gpt-oss-120b"))
    transcription_model: str = field(
        default_factory=lambda: _env("TRANSCRIPTION_MODEL", "whisper-large-v3-turbo")
    )
    # Characters of transcript per LLM request (keeps requests under free-tier token limits)
    llm_chunk_chars: int = field(default_factory=lambda: _env_int("LLM_CHUNK_CHARS", 12000))

    # ── Local models ───────────────────────────────────────────────────────
    whisper_model_size: str = field(default_factory=lambda: _env("WHISPER_MODEL", "base"))

    # ── Server / limits ────────────────────────────────────────────────────
    allowed_origins: list[str] = field(
        default_factory=lambda: _env_list(
            "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        )
    )
    max_upload_mb: int = field(default_factory=lambda: _env_int("MAX_UPLOAD_MB", 100))
    max_concurrent_jobs: int = field(default_factory=lambda: _env_int("MAX_CONCURRENT_JOBS", 2))
    # Uploads allowed per client IP per hour (0 disables the limit)
    uploads_per_hour: int = field(default_factory=lambda: _env_int("UPLOADS_PER_HOUR", 10))
    # Jobs (and their files) older than this are deleted automatically
    job_ttl_hours: int = field(default_factory=lambda: _env_int("JOB_TTL_HOURS", 48))

    data_dir: Path = field(
        default_factory=lambda: Path(_env("DATA_DIR", str(PROJECT_ROOT / "data"))).resolve()
    )
    frontend_dist: Path = field(
        default_factory=lambda: Path(
            _env("FRONTEND_DIST", str(PROJECT_ROOT / "frontend" / "dist"))
        ).resolve()
    )

    allowed_extensions: tuple[str, ...] = (
        ".mp3", ".wav", ".m4a", ".ogg", ".oga", ".opus", ".webm", ".flac", ".aac", ".mp4", ".mpeg",
    )

    @property
    def use_api(self) -> bool:
        if self.ai_provider == "api":
            return True
        if self.ai_provider == "local":
            return False
        return bool(self.api_key)

    @property
    def provider_name(self) -> str:
        if not self.use_api:
            return "local"
        return "groq" if "groq.com" in self.api_base_url else "openai-compatible"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


settings = Settings()
