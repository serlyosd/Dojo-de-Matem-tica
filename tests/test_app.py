from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services import OllamaService, WhisperService


def settings(tmp_path):
    return Settings(
        data_dir=tmp_path,
        ollama_url="http://ollama.invalid",
        ollama_model="modelo-simulado",
        whisper_cli="whisper-cli",
        whisper_model="modelo.bin",
        ffmpeg="ffmpeg",
    )


def test_text_confirmation_happens_before_simulated_analysis(tmp_path, monkeypatch):
    async def fake_analyze(self, activity, answer, input_type):
        assert answer == "24 dividido por 6 é 4"
        return "SIMULADO: cálculo conferido. Como você formou os grupos?"

    monkeypatch.setattr(OllamaService, "analyze", fake_analyze)
    with TestClient(create_app(settings(tmp_path))) as client:
        draft = client.post("/api/drafts/text", json={"text": "24 / 6 = quatro"})
        assert draft.status_code == 200
        result = client.post(
            "/api/analyze",
            json={"draft_id": draft.json()["draft_id"], "corrected_text": "24 dividido por 6 é 4"},
        )

    assert result.status_code == 200
    assert result.json()["analysis"].startswith("SIMULADO")


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
    def fake_transcribe(self, source, work_dir):
        assert source.read_bytes() == b"audio-ficticio"
        assert source.suffix == ".webm"
        return "Eu fiz vinte e quatro dividido por seis."

    monkeypatch.setattr(WhisperService, "transcribe", fake_transcribe)
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.post(
            "/api/drafts/audio",
            files={"file": ("gravacao.webm", b"audio-ficticio", "audio/webm")},
        )

    assert response.status_code == 200
    assert "vinte e quatro" in response.json()["reading"]
    assert list((tmp_path / "temp").iterdir()) == []


def test_rejects_unexpected_photo_format(tmp_path):
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.post("/api/drafts/photo", files={"file": ("x.svg", b"x", "image/svg+xml")})
    assert response.status_code == 415

