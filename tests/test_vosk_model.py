from app.vosk_model import LEGACY_MODEL_FILES, is_legacy_portuguese_model, resolve_model_dir


def create_legacy_model(path):
    path.mkdir(parents=True)
    for name in LEGACY_MODEL_FILES:
        (path / name).write_bytes(b"conteudo")
    (path / "ivector").mkdir()
    return path


def test_accepts_official_flat_legacy_structure(tmp_path):
    model = create_legacy_model(tmp_path / "vosk-model-small-pt-0.3")

    assert is_legacy_portuguese_model(model)
    assert resolve_model_dir(model) == model


def test_resolves_duplicated_model_directory(tmp_path):
    configured = tmp_path / "vosk-model-small-pt-0.3"
    nested = create_legacy_model(configured / "vosk-model-small-pt-0.3")

    assert resolve_model_dir(configured) == nested


def test_rejects_incomplete_legacy_structure(tmp_path):
    model = create_legacy_model(tmp_path / "vosk-model-small-pt-0.3")
    (model / "HCLr.fst").unlink()

    assert not is_legacy_portuguese_model(model)
    assert resolve_model_dir(model) is None


def test_rejects_phones_without_txt_extension(tmp_path):
    model = create_legacy_model(tmp_path / "vosk-model-small-pt-0.3")
    (model / "phones.txt").rename(model / "phones")

    assert not is_legacy_portuguese_model(model)
    assert resolve_model_dir(model) is None
