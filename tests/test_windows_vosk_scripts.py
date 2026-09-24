from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_download_script_validates_legacy_files_and_normalizes_nested_folder():
    script = (ROOT / "scripts" / "baixar_modelo_vosk.ps1").read_text(encoding="utf-8")

    for name in ("final.mdl", "Gr.fst", "HCLr.fst", "mfcc.conf", "phones", "word_boundary.int", "ivector"):
        assert name in script
    assert "Normalize-NestedModel" in script
    assert "Move-Item -Destination $target" in script
    assert script.index("Test-LegacyVoskModel $target") < script.index("Invoke-WebRequest")


def test_windows_verifier_normalizes_before_runtime_check():
    batch = (ROOT / "scripts" / "verificar_windows.bat").read_text(encoding="utf-8")
    verifier = (ROOT / "scripts" / "verificar_windows.ps1").read_text(encoding="utf-8")

    assert "baixar_modelo_vosk.ps1" in batch
    assert "-SomenteNormalizar" in batch
    assert "Resolve-VoskModel" in verifier
    assert "Model(os.environ['VOSK_MODEL_DIR'])" in verifier
