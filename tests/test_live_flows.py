import os
from pathlib import Path

import pytest


httpx = pytest.importorskip("httpx")


@pytest.mark.skipif(not os.getenv("DOJO_LIVE_AUDIO"), reason="defina DOJO_LIVE_AUDIO para teste local real")
def test_live_audio_endpoint():
    path = Path(os.environ["DOJO_LIVE_AUDIO"])
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=180) as client, path.open("rb") as source:
        response = client.post("/api/drafts/audio", files={"file": (path.name, source)})
    assert response.status_code == 200, response.text
    assert response.json()["reading"].strip()


@pytest.mark.skipif(not os.getenv("DOJO_LIVE_PHOTO"), reason="defina DOJO_LIVE_PHOTO para teste Ollama real")
def test_live_photo_endpoint():
    path = Path(os.environ["DOJO_LIVE_PHOTO"])
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=180) as client, path.open("rb") as source:
        response = client.post("/api/drafts/photo", files={"file": (path.name, source)})
    assert response.status_code == 200, response.text
    assert response.json()["reading"].strip()
