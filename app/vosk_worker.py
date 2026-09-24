from __future__ import annotations

import argparse
import json
import sys
import wave
from pathlib import Path


def transcribe(model_dir: Path, wav_path: Path) -> str:
    from vosk import KaldiRecognizer, Model, SetLogLevel

    SetLogLevel(-1)
    model = Model(str(model_dir))
    pieces: list[str] = []
    with wave.open(str(wav_path), "rb") as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2 or audio.getframerate() != 16_000:
            raise ValueError("O áudio convertido deve ser WAV mono PCM de 16 kHz.")
        recognizer = KaldiRecognizer(model, audio.getframerate())
        recognizer.SetWords(False)
        while chunk := audio.readframes(4_000):
            if recognizer.AcceptWaveform(chunk):
                text = json.loads(recognizer.Result()).get("text", "").strip()
                if text:
                    pieces.append(text)
        final_text = json.loads(recognizer.FinalResult()).get("text", "").strip()
        if final_text:
            pieces.append(final_text)
    return " ".join(pieces)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--audio", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        print(transcribe(arguments.model, arguments.audio), flush=True)
    except Exception as exc:
        print(f"Falha do Vosk: {exc}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
