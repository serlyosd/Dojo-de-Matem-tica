from __future__ import annotations

import asyncio
import base64
import shutil
from pathlib import Path

from .config import Settings


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


class WhisperService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _program(self, value: str) -> str | None:
        path = Path(value)
        if path.is_file():
            return str(path)
        return shutil.which(value)

    def status(self) -> dict[str, object]:
        whisper = self._program(self.settings.whisper_cli)
        model = Path(self.settings.whisper_model) if self.settings.whisper_model else None
        ffmpeg = self._program(self.settings.ffmpeg)
        missing = []
        if not whisper:
            missing.append("Whisper.cpp")
        if not model or not model.is_file():
            missing.append("modelo multilíngue do Whisper")
        if not ffmpeg:
            missing.append("FFmpeg")
        if missing:
            return {"ready": False, "message": "Falta: " + ", ".join(missing) + "."}
        return {"ready": True, "message": "Whisper.cpp, modelo e FFmpeg prontos."}

    async def _run(self, command: list[str], timeout: int, failure_message: str) -> None:
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            raise LocalComponentError(failure_message) from exc
        try:
            _, _ = await asyncio.wait_for(process.communicate(), timeout=timeout)
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

    async def transcribe(self, source: Path, work_dir: Path) -> str:
        status = self.status()
        if not status["ready"]:
            raise LocalComponentError(str(status["message"]))
        work_dir.mkdir(parents=True, exist_ok=True)
        wav_path = work_dir / f"{source.stem}.wav"
        await self._run(
            [
                str(self._program(self.settings.ffmpeg)), "-y", "-i", str(source),
                "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav_path),
            ],
            timeout=min(60, self.settings.audio_timeout_seconds),
            failure_message="Não consegui converter o áudio. Confira o FFmpeg e o formato gravado.",
        )

        output_prefix = work_dir / f"{source.stem}-transcricao"
        await self._run(
            [
                str(self._program(self.settings.whisper_cli)), "-m", self.settings.whisper_model,
                "-f", str(wav_path), "-l", "pt", "-otxt", "-of", str(output_prefix),
            ],
            timeout=self.settings.audio_timeout_seconds,
            failure_message="O Whisper.cpp não conseguiu transcrever o áudio.",
        )
        transcript_path = output_prefix.with_suffix(".txt")
        if not transcript_path.is_file():
            raise LocalComponentError("O Whisper.cpp terminou sem criar a transcrição.")
        return transcript_path.read_text(encoding="utf-8").strip()
