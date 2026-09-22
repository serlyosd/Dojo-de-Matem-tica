import json
import sys
import types
import wave

from app.vosk_worker import transcribe


class FakeRecognizer:
    def __init__(self, model, sample_rate):
        assert sample_rate == 16_000
        self.calls = 0

    def SetWords(self, enabled):
        assert enabled is False

    def AcceptWaveform(self, chunk):
        self.calls += 1
        return self.calls == 1

    def Result(self):
        return json.dumps({"text": "vinte e quatro dividido por seis"})

    def FinalResult(self):
        return json.dumps({"text": "é quatro"})


def test_worker_streams_wav_and_joins_vosk_results(tmp_path, monkeypatch):
    wav_path = tmp_path / "audio.wav"
    with wave.open(str(wav_path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16_000)
        audio.writeframes(b"\x00\x00" * 8_000)

    fake_vosk = types.SimpleNamespace(
        KaldiRecognizer=FakeRecognizer,
        Model=lambda path: object(),
        SetLogLevel=lambda level: None,
    )
    monkeypatch.setitem(sys.modules, "vosk", fake_vosk)

    result = transcribe(tmp_path / "modelo", wav_path)

    assert result == "vinte e quatro dividido por seis é quatro"
