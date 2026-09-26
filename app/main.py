from __future__ import annotations

import os
import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .analysis import ANALYZER_VERSION, analyze_basic_answer, evaluate_basic_answer
from .config import APP_VERSION, Settings
from .database import Database
from .services import LocalComponentError, OllamaService, VoskService
from .work_gate import WorkBusyError, WorkCancelledError, WorkGate, WorkTimeoutError


ROOT = Path(__file__).resolve().parents[1]
logger = logging.getLogger("dojo")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s — %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


class TextDraft(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class Confirmation(BaseModel):
    draft_id: int
    corrected_text: str = Field(min_length=1, max_length=4000)
    mission_id: str = Field(default="mission-default", min_length=1, max_length=100)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_environment()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = settings.data_dir / "temp"
    temp_dir.mkdir(exist_ok=True)
    db = Database(settings.data_dir / "dojo.db")
    db.initialize()
    ollama = OllamaService(settings)
    vosk = VoskService(settings)
    work_gate = WorkGate()

    app = FastAPI(title="Dojo da Matemática", version=APP_VERSION)
    app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(ROOT / "app" / "static" / "index.html")

    @app.get("/api/status")
    async def status() -> dict[str, object]:
        return {
            "app": {"ready": True, "message": f"Dojo v{APP_VERSION} pronto."},
            "analysis": {"ready": True, "message": "Conferência Python local pronta; não usa IA."},
            "processing": {
                "ready": not work_gate.busy,
                "message": "Livre para foto ou áudio." if not work_gate.busy else "Uma leitura está em andamento.",
            },
            "ollama": await ollama.status(),
            "vosk": vosk.status(),
        }

    @app.post("/api/drafts/text")
    async def text_draft(payload: TextDraft) -> dict[str, object]:
        draft_id = db.create_draft("text", payload.text.strip())
        return {"draft_id": draft_id, "reading": payload.text.strip(), "input_type": "text"}

    async def save_upload(upload: UploadFile, allowed: set[str], max_bytes: int) -> Path:
        content_type = (upload.content_type or "").split(";", 1)[0].lower()
        if content_type not in allowed:
            raise HTTPException(415, "Formato de arquivo não aceito nesta prova.")
        suffix = Path(upload.filename or "arquivo").suffix[:10]
        descriptor, name = tempfile.mkstemp(prefix="dojo-", suffix=suffix, dir=temp_dir)
        os.close(descriptor)
        target = Path(name)
        size = 0
        try:
            with target.open("wb") as output:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > max_bytes:
                        raise HTTPException(413, "O arquivo é maior que o limite desta prova.")
                    output.write(chunk)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return target

    @app.post("/api/drafts/photo")
    async def photo_draft(file: UploadFile = File(...)) -> dict[str, object]:
        path = await save_upload(file, {"image/jpeg", "image/png", "image/webp"}, 10 * 1024 * 1024)
        try:
            reading = await work_gate.run(
                lambda: ollama.read_photo(path),
                timeout_seconds=settings.photo_timeout_seconds,
            )
            draft_id = db.create_draft("photo", reading)
            return {"draft_id": draft_id, "reading": reading, "input_type": "photo"}
        except WorkBusyError as exc:
            raise HTTPException(429, "Já existe uma leitura em andamento. Aguarde ou cancele a tarefa atual.") from exc
        except WorkTimeoutError as exc:
            raise HTTPException(504, "A leitura da foto demorou demais e foi encerrada. Tente uma foto menor.") from exc
        except WorkCancelledError as exc:
            raise HTTPException(409, "A leitura da foto foi cancelada.") from exc
        except LocalComponentError as exc:
            logger.exception("Falha no fluxo de foto: %s", exc)
            raise HTTPException(503, f"Foto — {exc}") from exc
        finally:
            path.unlink(missing_ok=True)

    @app.post("/api/drafts/audio")
    async def audio_draft(file: UploadFile = File(...)) -> dict[str, object]:
        allowed = {"audio/webm", "audio/ogg", "audio/mp4", "audio/wav", "audio/x-wav", "video/webm"}
        path = await save_upload(file, allowed, 25 * 1024 * 1024)
        work_dir = Path(tempfile.mkdtemp(prefix="dojo-audio-", dir=temp_dir))
        try:
            reading = await work_gate.run(
                lambda: vosk.transcribe(path, work_dir),
                timeout_seconds=settings.audio_timeout_seconds,
            )
            if not reading:
                raise LocalComponentError("O áudio não produziu uma transcrição. Grave novamente.")
            draft_id = db.create_draft("audio", reading)
            return {"draft_id": draft_id, "reading": reading, "input_type": "audio"}
        except WorkBusyError as exc:
            raise HTTPException(429, "Já existe uma leitura em andamento. Aguarde ou cancele a tarefa atual.") from exc
        except WorkTimeoutError as exc:
            raise HTTPException(504, "A transcrição demorou demais e foi encerrada. Tente um áudio mais curto.") from exc
        except WorkCancelledError as exc:
            raise HTTPException(409, "A transcrição foi cancelada.") from exc
        except LocalComponentError as exc:
            logger.exception("Falha no fluxo de áudio: %s", exc)
            raise HTTPException(503, f"Áudio — {exc}") from exc
        finally:
            path.unlink(missing_ok=True)
            shutil.rmtree(work_dir, ignore_errors=True)

    @app.delete("/api/tasks/current")
    async def cancel_current_task() -> dict[str, object]:
        cancelled = work_gate.cancel()
        return {
            "cancelled": cancelled,
            "message": "Cancelamento solicitado." if cancelled else "Não há tarefa para cancelar.",
        }

    @app.post("/api/analyze")
    async def analyze(payload: Confirmation) -> dict[str, object]:
        row = db.confirm_draft(payload.draft_id, payload.corrected_text.strip())
        if row is None:
            raise HTTPException(404, "Rascunho não encontrado.")
        evaluation = evaluate_basic_answer(payload.corrected_text.strip())
        attempt = db.register_mission_result(payload.mission_id, evaluation.correct)
        analysis = analyze_basic_answer(payload.corrected_text.strip(), attempt or 1)
        db.save_analysis(payload.draft_id, analysis, ANALYZER_VERSION, APP_VERSION)
        return {
            "analysis": analysis,
            "correct": evaluation.correct,
            "wrong_attempts": attempt,
            "finished": evaluation.correct or attempt >= 3,
        }

    return app


app = create_app()
