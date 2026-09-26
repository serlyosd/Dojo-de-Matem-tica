from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    input_type TEXT NOT NULL CHECK(input_type IN ('text', 'photo', 'audio')),
    machine_reading TEXT NOT NULL,
    corrected_reading TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TEXT
);

CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_id INTEGER NOT NULL REFERENCES drafts(id),
    analysis_text TEXT NOT NULL,
    model_name TEXT NOT NULL,
    app_version TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mission_attempts (
    mission_id TEXT PRIMARY KEY,
    wrong_attempts INTEGER NOT NULL DEFAULT 0,
    completed INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def create_draft(self, input_type: str, reading: str) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO drafts (input_type, machine_reading) VALUES (?, ?)",
                (input_type, reading),
            )
            return int(cursor.lastrowid)

    def confirm_draft(self, draft_id: int, corrected_reading: str) -> sqlite3.Row | None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE drafts SET corrected_reading = ?, confirmed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (corrected_reading, draft_id),
            )
            return connection.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()

    def save_analysis(self, draft_id: int, text: str, model: str, version: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO analyses (draft_id, analysis_text, model_name, app_version) VALUES (?, ?, ?, ?)",
                (draft_id, text, model, version),
            )

    def register_mission_result(self, mission_id: str, correct: bool) -> int:
        with self.connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO mission_attempts (mission_id) VALUES (?)", (mission_id,)
            )
            if correct:
                connection.execute(
                    "UPDATE mission_attempts SET completed = 1, updated_at = CURRENT_TIMESTAMP WHERE mission_id = ?",
                    (mission_id,),
                )
            else:
                connection.execute(
                    "UPDATE mission_attempts SET wrong_attempts = MIN(wrong_attempts + 1, 3), "
                    "updated_at = CURRENT_TIMESTAMP WHERE mission_id = ?",
                    (mission_id,),
                )
            row = connection.execute(
                "SELECT wrong_attempts FROM mission_attempts WHERE mission_id = ?", (mission_id,)
            ).fetchone()
            return int(row["wrong_attempts"])
