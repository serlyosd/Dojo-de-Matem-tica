from __future__ import annotations

from pathlib import Path


LEGACY_MODEL_FILES = (
    "final.mdl",
    "Gr.fst",
    "HCLr.fst",
    "mfcc.conf",
    "phones.txt",
    "word_boundary.int",
)


def is_legacy_portuguese_model(path: Path) -> bool:
    return (
        path.is_dir()
        and all((path / name).exists() for name in LEGACY_MODEL_FILES)
        and (path / "ivector").is_dir()
    )


def resolve_model_dir(configured_path: str | Path) -> Path | None:
    """Aceita o modelo flat oficial e uma extração duplicada comum no Windows."""
    path = Path(configured_path)
    if is_legacy_portuguese_model(path):
        return path
    nested = path / path.name
    if is_legacy_portuguese_model(nested):
        return nested
    return None
