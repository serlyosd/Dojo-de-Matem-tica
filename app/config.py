from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


APP_VERSION = "0.1.1"


def default_data_dir() -> Path:
    if local_app_data := os.getenv("LOCALAPPDATA"):
        return Path(local_app_data) / "DojoDaMatematica"
    return Path(__file__).resolve().parents[1] / "data"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    ollama_url: str
    ollama_model: str
    whisper_cli: str
    whisper_model: str
    ffmpeg: str
    photo_timeout_seconds: int = 90
    audio_timeout_seconds: int = 240

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            data_dir=Path(os.getenv("DOJO_DATA_DIR", default_data_dir())),
            ollama_url=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen3-vl:4b"),
            whisper_cli=os.getenv("WHISPER_CLI", "whisper-cli"),
            whisper_model=os.getenv("WHISPER_MODEL", ""),
            ffmpeg=os.getenv("FFMPEG", "ffmpeg"),
            photo_timeout_seconds=_bounded_timeout("PHOTO_TIMEOUT_SECONDS", 90),
            audio_timeout_seconds=_bounded_timeout("AUDIO_TIMEOUT_SECONDS", 240),
        )


def _bounded_timeout(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return min(max(value, 10), 600)
