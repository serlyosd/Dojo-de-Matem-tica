from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnóstico ponta a ponta do Dojo da Matemática")
    parser.add_argument("--audio", type=Path, help="arquivo local WAV, WebM, OGG ou M4A")
    parser.add_argument("--foto", type=Path, help="arquivo local JPG, PNG ou WebP")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    failed = False
    with httpx.Client(base_url=args.url, timeout=180) as client:
        try:
            status = client.get("/api/status").json()
            print("[STATUS]", status)
        except Exception as exc:
            print(f"[FALHA] Aplicativo não respondeu: {exc}")
            return 1
        for label, path, endpoint in (
            ("ÁUDIO", args.audio, "/api/drafts/audio"),
            ("FOTO", args.foto, "/api/drafts/photo"),
        ):
            if path is None:
                print(f"[PULADO] {label}: nenhum arquivo informado")
                continue
            try:
                with path.open("rb") as source:
                    response = client.post(endpoint, files={"file": (path.name, source)})
                body = response.json()
                if response.is_success and body.get("reading"):
                    print(f"[PRONTO] {label}: {body['reading']}")
                else:
                    failed = True
                    print(f"[FALHA] {label}: HTTP {response.status_code} — {body.get('detail', body)}")
            except Exception as exc:
                failed = True
                print(f"[FALHA] {label}: {type(exc).__name__}: {exc}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
