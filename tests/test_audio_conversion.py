import asyncio
import wave
from pathlib import Path

import pytest

from app.config import Settings
from app.services import LocalComponentError, VoskService
from app.vosk_model import LEGACY_MODEL_FILES


def write_wav(path: Path, seconds: float = 0.1) -> None:
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16_000)
        audio.writeframes(b"\x00\x00" * int(16_000 * seconds))


class FakeProcess:
    def __init__(self, command, calls):
        self.command = command
        self.calls = calls
        self.returncode = 0
        self.killed = False

    async def communicate(self):
        self.calls.append(self.command)
        if "ffmpeg" in Path(self.command[0]).name:
            write_wav(Path(self.command[-1]))
            return b"", b""
        return "vinte e quatro dividido por seis é quatro\n".encode(), b""

    def kill(self):
        self.killed = True
        self.returncode = -1


class HangingProcess(FakeProcess):
    def __init__(self, command, calls):
        super().__init__(command, calls)
        self.finished = asyncio.Event()

    async def communicate(self):
        await self.finished.wait()
        return b"", b""

    def kill(self):
        super().kill()
        self.finished.set()


def make_service(tmp_path, max_audio_seconds=60):
    ffmpeg = tmp_path / "ffmpeg.exe"
    model = tmp_path / "vosk-model-small-pt-0.3"
    model.mkdir(parents=True)
    for name in LEGACY_MODEL_FILES:
        (model / name).write_bytes(b"modelo")
    (model / "ivector").mkdir()
    ffmpeg.write_bytes(b"ficticio")
    return VoskService(
        Settings(
            data_dir=tmp_path,
            ollama_url="url",
            ollama_model="model",
            vosk_model_dir=str(model),
            ffmpeg=str(ffmpeg),
            max_audio_seconds=max_audio_seconds,
        )
    )


def test_audio_conversion_uses_one_thread_and_vosk_worker(tmp_path, monkeypatch):
    service = make_service(tmp_path)
    source = tmp_path / "gravacao.webm"
    source.write_bytes(b"webm-ficticio")
    calls = []

    async def fake_subprocess(*command, **kwargs):
        assert kwargs["env"]["OMP_NUM_THREADS"] == "1"
        assert kwargs["env"]["OPENBLAS_NUM_THREADS"] == "1"
        return FakeProcess(list(command), calls)

    monkeypatch.setattr("app.services.asyncio.create_subprocess_exec", fake_subprocess)
    monkeypatch.setattr("app.services.importlib.util.find_spec", lambda name: object())

    result = asyncio.run(service.transcribe(source, tmp_path / "work"))

    assert result == "vinte e quatro dividido por seis é quatro"
    assert "-threads" in calls[0]
    assert calls[0][calls[0].index("-threads") + 1] == "1"
    assert calls[0][calls[0].index("-ar") + 1] == "16000"
    assert calls[0][calls[0].index("-ac") + 1] == "1"
    assert Path(calls[1][1]).name == "vosk_worker.py"
    assert "vosk-model-small-pt-0.3" in calls[1][calls[1].index("--model") + 1]


def test_audio_over_duration_limit_is_rejected_before_vosk(tmp_path, monkeypatch):
    service = make_service(tmp_path, max_audio_seconds=10)
    source = tmp_path / "longo.webm"
    source.write_bytes(b"audio")
    calls = []

    async def fake_subprocess(*command, **kwargs):
        process = FakeProcess(list(command), calls)

        async def long_audio():
            calls.append(process.command)
            write_wav(Path(process.command[-1]), seconds=11)
            return b"", b""

        process.communicate = long_audio
        return process

    monkeypatch.setattr("app.services.asyncio.create_subprocess_exec", fake_subprocess)
    monkeypatch.setattr("app.services.importlib.util.find_spec", lambda name: object())

    with pytest.raises(LocalComponentError, match="passa de 10 segundos"):
        asyncio.run(service.transcribe(source, tmp_path / "work"))
    assert len(calls) == 1


def test_cancellation_kills_local_process(tmp_path, monkeypatch):
    service = make_service(tmp_path)
    processes = []

    async def fake_subprocess(*command, **kwargs):
        process = HangingProcess(list(command), [])
        processes.append(process)
        return process

    monkeypatch.setattr("app.services.asyncio.create_subprocess_exec", fake_subprocess)

    async def scenario():
        task = asyncio.create_task(service._run(["programa"], 30, "falhou", "teste"))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert processes[0].killed


def test_timeout_kills_local_process(tmp_path, monkeypatch):
    service = make_service(tmp_path)
    processes = []

    async def fake_subprocess(*command, **kwargs):
        process = HangingProcess(list(command), [])
        processes.append(process)
        return process

    monkeypatch.setattr("app.services.asyncio.create_subprocess_exec", fake_subprocess)

    with pytest.raises(LocalComponentError, match="Tempo limite atingido"):
        asyncio.run(service._run(["programa"], 0.01, "falhou", "teste"))
    assert processes[0].killed


def test_status_explains_missing_vosk_and_ffmpeg(tmp_path, monkeypatch):
    service = VoskService(Settings(tmp_path, "url", "model", "modelo-ausente", "ffmpeg-ausente"))
    monkeypatch.setattr("app.services.importlib.util.find_spec", lambda name: None)

    status = service.status()

    assert status["ready"] is False
    assert "biblioteca Python Vosk" in status["message"]
    assert "modelo português pequeno do Vosk" in status["message"]
    assert "FFmpeg" in status["message"]


def test_service_accepts_duplicated_legacy_model_folder(tmp_path, monkeypatch):
    ffmpeg = tmp_path / "ffmpeg.exe"
    ffmpeg.write_bytes(b"ficticio")
    configured = tmp_path / "vosk-model-small-pt-0.3"
    nested = configured / "vosk-model-small-pt-0.3"
    nested.mkdir(parents=True)
    for name in LEGACY_MODEL_FILES:
        (nested / name).write_bytes(b"modelo")
    (nested / "ivector").mkdir()
    service = VoskService(Settings(tmp_path, "url", "model", str(configured), str(ffmpeg)))
    monkeypatch.setattr("app.services.importlib.util.find_spec", lambda name: object())

    status = service.status()

    assert status == {"ready": True, "message": "Vosk português pequeno e FFmpeg prontos."}


def test_process_error_exposes_stderr_and_stage(tmp_path, monkeypatch, caplog):
    service = make_service(tmp_path)
    process = FakeProcess(["ffmpeg"], [])
    process.returncode = 1

    async def failed_communicate():
        return b"", "codec WebM não suportado".encode()

    process.communicate = failed_communicate
    monkeypatch.setattr(
        "app.services.asyncio.create_subprocess_exec", lambda *args, **kwargs: asyncio.sleep(0, result=process)
    )

    with pytest.raises(LocalComponentError, match="codec WebM não suportado"):
        asyncio.run(service._run(["ffmpeg"], 10, "Falha de conversão.", "FFmpeg"))
    assert "Etapa FFmpeg" in caplog.text
    assert "stderr=codec WebM não suportado" in caplog.text
