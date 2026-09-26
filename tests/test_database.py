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


def test_mission_wrong_attempts_are_capped_at_three(tmp_path):
    database = Database(tmp_path / "dojo.db")
    database.initialize()

    assert [database.register_mission_result("mission-1", False) for _ in range(4)] == [1, 2, 3, 3]
    with database.connect() as connection:
        row = connection.execute(
            "SELECT wrong_attempts, completed FROM mission_attempts WHERE mission_id = ?", ("mission-1",)
        ).fetchone()
    assert tuple(row) == (3, 0)


def test_correct_answer_marks_mission_completed(tmp_path):
    database = Database(tmp_path / "dojo.db")
    database.initialize()
    database.register_mission_result("mission-ok", True)
    with database.connect() as connection:
        completed = connection.execute(
            "SELECT completed FROM mission_attempts WHERE mission_id = ?", ("mission-ok",)
        ).fetchone()[0]
    assert completed == 1
