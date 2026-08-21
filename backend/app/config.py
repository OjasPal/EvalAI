import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_DIR / ".env")


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _labels(raw: str | None) -> tuple[str, ...]:
    if not raw or not raw.strip():
        return ("A", "B")
    labels = tuple(label.strip() for label in raw.split(",") if label.strip())
    return labels or ("A", "B")


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "EvalAI")
    model_path: str = os.getenv(
        "MODEL_PATH", "notebooks/roberta_reward_model_FINAL"
    )
    use_dummy_model: bool = _bool(os.getenv("USE_DUMMY_MODEL"), False)
    max_length: int = int(os.getenv("MAX_LENGTH", "256"))
    ollama_url: str = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
    generation_model_a: str = os.getenv("GENERATION_MODEL_A", "llama3.2")
    generation_model_b: str = os.getenv("GENERATION_MODEL_B", "qwen2.5:3b")
    generation_timeout: int = int(os.getenv("GENERATION_TIMEOUT", "120"))
    feedback_file: str = os.getenv(
        "FEEDBACK_FILE", str(BACKEND_DIR / "data" / "feedback.jsonl")
    )
    model_label_mapping: tuple[str, ...] = field(
        default_factory=lambda: _labels(os.getenv("MODEL_LABEL_MAPPING"))
    )
    project_root: Path = PROJECT_ROOT
    cors_origins: list[str] = field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "*").split(",")
            if origin.strip()
        ]
    )


settings = Settings()
