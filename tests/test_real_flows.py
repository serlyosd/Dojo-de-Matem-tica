import json
import stat
import sys
import threading
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.vosk_model import LEGACY_MODEL_FILES


def _wav(path):
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16_000)
        audio.writeframes(b"\0\0" * 1_600)


def _legacy_model(path):
    path.mkdir()
    for name in LEGACY_MODEL_FILES:
        (path / name).write_bytes(b"x")
    (path / "ivector").mkdir()


def test_local_wav_crosses_upload_ffmpeg_worker_and_api(tmp_path, monkeypatch):
    audio = tmp_path / "fala.wav"; _wav(audio)
    model = tmp_path / "vosk-model-small-pt-0.3"; _legacy_model(model)
    fake_package = tmp_path / "deps" / "vosk"; fake_package.mkdir(parents=True)
    fake_package.joinpath("__init__.py").write_text(
        "import json\nclass Model:\n def __init__(self,p): pass\n"
        "class KaldiRecognizer:\n def __init__(self,m,r): pass\n def SetWords(self,x): pass\n"
        " def AcceptWaveform(self,x): return False\n def Result(self): return json.dumps({'text':''})\n"
        " def FinalResult(self): return json.dumps({'text':'quatro veiculos'})\n"
        "def SetLogLevel(x): pass\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path / "deps"))
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "deps") + ":" + str(tmp_path))
    ffmpeg = tmp_path / "ffmpeg"
    ffmpeg.write_text(
        f"#!{sys.executable}\nimport shutil,sys\nshutil.copyfile(sys.argv[sys.argv.index('-i')+1],sys.argv[-1])\n",
        encoding="utf-8")
    ffmpeg.chmod(ffmpeg.stat().st_mode | stat.S_IEXEC)
    settings = Settings(tmp_path / "data", "http://unused", "qwen", str(model), str(ffmpeg))

    with TestClient(create_app(settings)) as client, audio.open("rb") as source:
        response = client.post("/api/drafts/audio", files={"file": ("fala.wav", source, "audio/wav")})

    assert response.status_code == 200, response.text
    assert response.json()["reading"] == "quatro veiculos"


def test_photo_endpoint_sends_real_ollama_generate_payload(tmp_path):
    captured = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            size = int(self.headers["Content-Length"])
            captured.update(json.loads(self.rfile.read(size)))
            body = json.dumps({"response": "24 dividido por 6 = 4"}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    settings = Settings(tmp_path / "data", f"http://127.0.0.1:{server.server_port}", "qwen3-vl:4b", "missing", "missing")
    try:
        with TestClient(create_app(settings)) as client:
            response = client.post("/api/drafts/photo", files={"file": ("conta.png", b"png", "image/png")})
    finally:
        server.shutdown(); thread.join()

    assert response.status_code == 200, response.text
    assert response.json()["reading"] == "24 dividido por 6 = 4"
    assert captured["model"] == "qwen3-vl:4b"
    assert captured["stream"] is False
    assert captured["images"]
    assert captured["keep_alive"] == 0
