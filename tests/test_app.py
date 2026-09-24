import pytest


pytest.importorskip("fastapi", reason="FastAPI não está instalado neste ambiente")

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services import OllamaService, VoskService


def settings(tmp_path):
    return Settings(
        data_dir=tmp_path,
        ollama_url="http://ollama.invalid",
        ollama_model="modelo-simulado",
        vosk_model_dir="modelo-vosk",
        ffmpeg="ffmpeg",
    )


def test_text_confirmation_happens_before_simulated_analysis(tmp_path, monkeypatch):
    async def forbidden_ollama_call(*args, **kwargs):
        raise AssertionError("Ollama não pode analisar texto")

    monkeypatch.setattr(OllamaService, "_generate", forbidden_ollama_call)
    with TestClient(create_app(settings(tmp_path))) as client:
        draft = client.post("/api/drafts/text", json={"text": "24 / 6 = quatro"})
        assert draft.status_code == 200
        result = client.post(
            "/api/analyze",
            json={"draft_id": draft.json()["draft_id"], "corrected_text": "24 dividido por 6 é 4"},
        )

    assert result.status_code == 200
    assert "Conferência local: 24 ÷ 6 = 4" in result.json()["analysis"]
    assert "quantidade final de 4 veículos está correta" in result.json()["analysis"]


def test_photo_reading_is_returned_for_mandatory_review(tmp_path, monkeypatch):
    async def fake_read_photo(self, path):
        assert path.read_bytes() == b"imagem-ficticia"
        return "24 / G = 4"

    monkeypatch.setattr(OllamaService, "read_photo", fake_read_photo)
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.post(
            "/api/drafts/photo",
            files={"file": ("conta.png", b"imagem-ficticia", "image/png")},
        )

    assert response.status_code == 200
    assert response.json()["reading"] == "24 / G = 4"
    assert response.json()["draft_id"]
    assert list((tmp_path / "temp").iterdir()) == []


def test_browser_audio_is_passed_to_local_transcriber(tmp_path, monkeypatch):
    async def fake_transcribe(self, source, work_dir):
        assert source.read_bytes() == b"audio-ficticio"
        assert source.suffix == ".webm"
        return "Eu fiz vinte e quatro dividido por seis."

    monkeypatch.setattr(VoskService, "transcribe", fake_transcribe)
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.post(
            "/api/drafts/audio",
            files={"file": ("gravacao.webm", b"audio-ficticio", "audio/webm")},
        )

    assert response.status_code == 200
    assert "vinte e quatro" in response.json()["reading"]
    assert list((tmp_path / "temp").iterdir()) == []
    with TestClient(create_app(settings(tmp_path))) as client:
        corrected = client.post(
            "/api/analyze",
            json={"draft_id": response.json()["draft_id"], "corrected_text": "24 dividido por 6 é 4"},
        )
    assert corrected.status_code == 200
    assert "quantidade final de 4 veículos está correta" in corrected.json()["analysis"]


def test_rejects_unexpected_photo_format(tmp_path):
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.post("/api/drafts/photo", files={"file": ("x.svg", b"x", "image/svg+xml")})
    assert response.status_code == 415


def test_basic_analysis_does_not_require_ollama_running(tmp_path, monkeypatch):
    async def offline_status(self):
        return {"ready": False, "message": "Ollama não respondeu."}

    monkeypatch.setattr(OllamaService, "status", offline_status)
    with TestClient(create_app(settings(tmp_path))) as client:
        draft = client.post("/api/drafts/text", json={"text": "A resposta é 3"}).json()
        result = client.post(
            "/api/analyze",
            json={"draft_id": draft["draft_id"], "corrected_text": "A resposta é 3"},
        )

    assert result.status_code == 200
    assert "ainda não corresponde a 4 veículos" in result.json()["analysis"]
