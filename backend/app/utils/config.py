from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(BACKEND_DIR / ".env")


def _csv_env(name: str, default: str) -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    catalog_path: Path = Path(os.getenv("SHL_CATALOG_PATH", BACKEND_DIR / "data" / "catalog.json"))
    seed_catalog_path: Path = BACKEND_DIR / "data" / "catalog.seed.json"
    chroma_path: Path = Path(os.getenv("SHL_CHROMA_PATH", BACKEND_DIR / "data" / "chroma"))
    collection_name: str = os.getenv("SHL_CHROMA_COLLECTION", "shl_individual_tests")
    embedding_model: str = os.getenv("SHL_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_flash_model: str = os.getenv("GEMINI_FLASH_MODEL", "gemini-1.5-flash")
    gemini_pro_model: str = os.getenv("GEMINI_PRO_MODEL", "gemini-1.5-pro")
    gemini_timeout_seconds: float = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "12"))
    enable_gemini: bool = os.getenv("ENABLE_GEMINI", "true").lower() in {"1", "true", "yes"}
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    cors_origins: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "cors_origins",
            _csv_env(
                "CORS_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000",
            ),
        )


settings = Settings()
