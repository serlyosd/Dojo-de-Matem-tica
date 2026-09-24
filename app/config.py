from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


APP_VERSION = "0.1.2"


def default_data_dir() -> Path:
    if local_app_data := os.getenv("LOCALAPPDATA"):
        return Path(local_app_data) / "DojoDaMatematica"
    return Path(__file__).resolve().parents[1] / "data"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    ollama_url: str
    ollama_model: str
    vosk_model_dir: str
    ffmpeg: str
    photo_timeout_seconds: int = 90
    audio_timeout_seconds: int = 120
    max_audio_seconds: int = 60

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            data_dir=Path(os.getenv("DOJO_DATA_DIR", default_data_dir())),
            ollama_url=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen3-vl:4b"),
            vosk_model_dir=os.getenv("VOSK_MODEL_DIR", ""),
            ffmpeg=os.getenv("FFMPEG", "ffmpeg"),
            photo_timeout_seconds=_bounded_timeout("PHOTO_TIMEOUT_SECONDS", 90),
            audio_timeout_seconds=_bounded_timeout("AUDIO_TIMEOUT_SECONDS", 120),
            max_audio_seconds=_bounded_timeout("MAX_AUDIO_SECONDS", 60, maximum=120),
        )


def _bounded_timeout(name: str, default: int, maximum: int = 600) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return min(max(value, 10), maximum)
