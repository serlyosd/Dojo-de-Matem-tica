import asyncio
from pathlib import Path

from app.config import Settings
from app.services import WhisperService


class FakeProcess:
    def __init__(self, command, calls):
        self.command = command
        self.calls = calls
        self.returncode = 0
        self.killed = False

    async def communicate(self):
        self.calls.append(self.command)
        if "-otxt" in self.command:
            prefix = Path(self.command[self.command.index("-of") + 1])
            prefix.with_suffix(".txt").write_text("transcrição simulada", encoding="utf-8")
        return b"", b""

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


def test_audio_conversion_and_whisper_command(tmp_path, monkeypatch):
    ffmpeg = tmp_path / "ffmpeg.exe"
    whisper = tmp_path / "whisper-cli.exe"
    model = tmp_path / "ggml-small.bin"
    for file in (ffmpeg, whisper, model):
        file.write_bytes(b"ficticio")
    source = tmp_path / "gravacao.webm"
    source.write_bytes(b"webm-ficticio")
    calls = []

    async def fake_subprocess(*command, **kwargs):
        return FakeProcess(list(command), calls)

    monkeypatch.setattr("app.services.asyncio.create_subprocess_exec", fake_subprocess)
    service = WhisperService(Settings(tmp_path, "url", "model", str(whisper), str(model), str(ffmpeg)))

    result = asyncio.run(service.transcribe(source, tmp_path / "work"))

    assert result == "transcrição simulada"
    assert calls[0][0] == str(ffmpeg)
    assert calls[0][calls[0].index("-ar") + 1] == "16000"
    assert calls[0][calls[0].index("-ac") + 1] == "1"
    assert calls[1][0] == str(whisper)
    assert calls[1][calls[1].index("-l") + 1] == "pt"


def test_cancellation_kills_local_process(tmp_path, monkeypatch):
    service = WhisperService(Settings(tmp_path, "url", "model", "whisper", "model.bin", "ffmpeg"))
    processes = []

    async def fake_subprocess(*command, **kwargs):
        process = HangingProcess(list(command), [])
        processes.append(process)
        return process

    monkeypatch.setattr("app.services.asyncio.create_subprocess_exec", fake_subprocess)

    async def scenario():
        task = asyncio.create_task(service._run(["programa"], 30, "falhou"))
        await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(scenario())
    assert processes[0].killed
