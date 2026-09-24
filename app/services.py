from __future__ import annotations

import asyncio
import base64
import importlib.util
import os
import shutil
import sys
import wave
from pathlib import Path

from .config import Settings
from .vosk_model import resolve_model_dir


class LocalComponentError(RuntimeError):
    """Erro esperado de um componente instalado no computador."""


class OllamaService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def _generate(self, prompt: str, images: list[str]) -> str:
        import httpx

        payload: dict[str, object] = {
            "model": self.settings.ollama_model,
            "prompt": prompt,
            "stream": False,
        }
        payload["images"] = images
        try:
            timeout = httpx.Timeout(self.settings.photo_timeout_seconds)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(f"{self.settings.ollama_url}/api/generate", json=payload)
                response.raise_for_status()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            raise LocalComponentError(
                "Não consegui conversar com o Ollama. Abra o Ollama e confira o modelo configurado."
            ) from exc
        try:
            answer = response.json().get("response", "").strip()
        except (ValueError, AttributeError) as exc:
            raise LocalComponentError("O Ollama devolveu uma resposta inválida. Tente novamente.") from exc
        if not answer:
            raise LocalComponentError("O Ollama respondeu sem texto. Tente novamente.")
        return answer

    async def read_photo(self, path: Path) -> str:
        image = base64.b64encode(path.read_bytes()).decode("ascii")
        prompt = (
            "Transcreva somente o que está visível nesta foto de uma atividade de matemática. "
            "Preserve números, vírgulas, sinais, linhas e a resposta da estudante. "
            "Não corrija, não avalie e não complete partes ilegíveis. Marque partes ilegíveis como [ilegível]. "
            "Responda em português brasileiro apenas com a transcrição."
        )
        return await self._generate(prompt, [image])

    async def status(self) -> dict[str, object]:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=4) as client:
                response = await client.get(f"{self.settings.ollama_url}/api/tags")
                response.raise_for_status()
                models = [item.get("name", "") for item in response.json().get("models", [])]
        except (httpx.HTTPError, ValueError, AttributeError):
            return {"ready": False, "message": "Ollama não respondeu."}
        wanted = self.settings.ollama_model
        available = any(name == wanted or name.startswith(f"{wanted}:") for name in models)
        return {
            "ready": available,
            "message": "Ollama e modelo prontos." if available else f"Ollama aberto; falta o modelo {wanted}.",
        }


class VoskService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _program(self, value: str) -> str | None:
        path = Path(value)
        if path.is_file():
            return str(path)
        return shutil.which(value)

    def status(self) -> dict[str, object]:
        model = resolve_model_dir(self.settings.vosk_model_dir) if self.settings.vosk_model_dir else None
        ffmpeg = self._program(self.settings.ffmpeg)
        missing = []
        if importlib.util.find_spec("vosk") is None:
            missing.append("biblioteca Python Vosk")
        if model is None:
            missing.append("modelo português pequeno do Vosk")
        if not ffmpeg:
            missing.append("FFmpeg")
        if missing:
            return {"ready": False, "message": "Falta: " + ", ".join(missing) + "."}
        return {"ready": True, "message": "Vosk português pequeno e FFmpeg prontos."}

    async def _run(self, command: list[str], timeout: int, failure_message: str) -> bytes:
        environment = os.environ.copy()
        environment.update({"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"})
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=environment,
            )
        except OSError as exc:
            raise LocalComponentError(failure_message) from exc
        try:
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except TimeoutError as exc:
            process.kill()
            await process.communicate()
            raise LocalComponentError(f"{failure_message} Tempo limite atingido.") from exc
        except asyncio.CancelledError:
            process.kill()
            await process.communicate()
            raise
        if process.returncode != 0:
            raise LocalComponentError(failure_message)
        return stdout

    def _duration(self, wav_path: Path) -> float:
        try:
            with wave.open(str(wav_path), "rb") as audio:
                return audio.getnframes() / audio.getframerate()
        except (wave.Error, OSError, ZeroDivisionError) as exc:
            raise LocalComponentError("O FFmpeg criou um áudio inválido. Grave novamente.") from exc

    async def transcribe(self, source: Path, work_dir: Path) -> str:
        status = self.status()
        if not status["ready"]:
            raise LocalComponentError(str(status["message"]))
        model_dir = resolve_model_dir(self.settings.vosk_model_dir)
        if model_dir is None:
            raise LocalComponentError("A estrutura do modelo português pequeno do Vosk é inválida.")
        work_dir.mkdir(parents=True, exist_ok=True)
        wav_path = work_dir / f"{source.stem}.wav"
        await self._run(
            [
                str(self._program(self.settings.ffmpeg)), "-y", "-i", str(source),
                "-t", str(self.settings.max_audio_seconds + 1), "-threads", "1",
                "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav_path),
            ],
            timeout=min(60, self.settings.audio_timeout_seconds),
            failure_message="Não consegui converter o áudio. Confira o FFmpeg e o formato gravado.",
        )
        if self._duration(wav_path) > self.settings.max_audio_seconds:
            raise LocalComponentError(
                f"O áudio passa de {self.settings.max_audio_seconds} segundos. Grave uma explicação mais curta."
            )

        stdout = await self._run(
            [
                sys.executable, "-m", "app.vosk_worker",
                "--model", str(model_dir),
                "--audio", str(wav_path),
            ],
            timeout=self.settings.audio_timeout_seconds,
            failure_message=(
                "O Vosk não conseguiu transcrever. Confira o modelo português e a compatibilidade do processador."
            ),
        )
        try:
            return stdout.decode("utf-8").strip()
        except UnicodeDecodeError as exc:
            raise LocalComponentError("O Vosk devolveu uma transcrição inválida.") from exc
