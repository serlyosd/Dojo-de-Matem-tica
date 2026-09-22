from app.database import Database


def test_minimal_history_keeps_machine_and_corrected_readings(tmp_path):
    database = Database(tmp_path / "dojo.db")
    database.initialize()
    draft_id = database.create_draft("photo", "24 / G")

    row = database.confirm_draft(draft_id, "24 / 6 = 4")
    database.save_analysis(draft_id, "Leitura confirmada.", "modelo-teste", "0.1.0")

    assert row["machine_reading"] == "24 / G"
    assert row["corrected_reading"] == "24 / 6 = 4"
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM analyses").fetchone()[0] == 1

