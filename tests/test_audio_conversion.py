from pathlib import Path
from types import SimpleNamespace

from app.config import Settings
from app.services import WhisperService


def test_audio_conversion_and_whisper_command(tmp_path, monkeypatch):
    ffmpeg = tmp_path / "ffmpeg.exe"
    whisper = tmp_path / "whisper-cli.exe"
    model = tmp_path / "ggml-small.bin"
    for file in (ffmpeg, whisper, model):
        file.write_bytes(b"ficticio")
    source = tmp_path / "gravacao.webm"
    source.write_bytes(b"webm-ficticio")
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if "-otxt" in command:
            prefix = Path(command[command.index("-of") + 1])
            prefix.with_suffix(".txt").write_text("transcrição simulada", encoding="utf-8")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("app.services.subprocess.run", fake_run)
    service = WhisperService(Settings(tmp_path, "url", "model", str(whisper), str(model), str(ffmpeg)))

    result = service.transcribe(source, tmp_path / "work")

    assert result == "transcrição simulada"
    assert calls[0][0] == str(ffmpeg)
    assert calls[0][calls[0].index("-ar") + 1] == "16000"
    assert calls[0][calls[0].index("-ac") + 1] == "1"
    assert calls[1][0] == str(whisper)
    assert calls[1][calls[1].index("-l") + 1] == "pt"
