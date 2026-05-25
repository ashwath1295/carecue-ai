from __future__ import annotations

import sqlite3
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any


DB_PATH = Path(__file__).with_name("carecue.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def create_tables() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS children (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age TEXT NOT NULL,
                usual_wake_time TEXT,
                usual_nap_time TEXT,
                usual_bedtime TEXT,
                known_triggers TEXT,
                comfort_actions TEXT,
                food_preferences TEXT,
                notes TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                child_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                event_time TEXT NOT NULL,
                details TEXT,
                mood TEXT,
                intensity INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (child_id) REFERENCES children(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS ai_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                child_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (child_id) REFERENCES children(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS ai_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                child_id INTEGER NOT NULL,
                feedback TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (question_id) REFERENCES ai_questions(id) ON DELETE CASCADE,
                FOREIGN KEY (child_id) REFERENCES children(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS child_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                child_id INTEGER NOT NULL,
                pattern_type TEXT NOT NULL,
                pattern_summary TEXT NOT NULL,
                confidence TEXT,
                last_updated TEXT NOT NULL,
                FOREIGN KEY (child_id) REFERENCES children(id) ON DELETE CASCADE
            );
            """
        )


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def create_child(data: dict[str, Any]) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO children (
                name, age, usual_wake_time, usual_nap_time, usual_bedtime,
                known_triggers, comfort_actions, food_preferences, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("name", "").strip(),
                str(data.get("age", "")).strip(),
                data.get("usual_wake_time", ""),
                data.get("usual_nap_time", ""),
                data.get("usual_bedtime", ""),
                data.get("known_triggers", ""),
                data.get("comfort_actions", ""),
                data.get("food_preferences", ""),
                data.get("notes", ""),
                _now(),
            ),
        )
        return int(cur.lastrowid)


def update_child(child_id: int, data: dict[str, Any]) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE children
            SET name = ?, age = ?, usual_wake_time = ?, usual_nap_time = ?,
                usual_bedtime = ?, known_triggers = ?, comfort_actions = ?,
                food_preferences = ?, notes = ?
            WHERE id = ?
            """,
            (
                data.get("name", "").strip(),
                str(data.get("age", "")).strip(),
                data.get("usual_wake_time", ""),
                data.get("usual_nap_time", ""),
                data.get("usual_bedtime", ""),
                data.get("known_triggers", ""),
                data.get("comfort_actions", ""),
                data.get("food_preferences", ""),
                data.get("notes", ""),
                child_id,
            ),
        )


def get_children() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM children ORDER BY created_at DESC").fetchall()
        return rows_to_dicts(rows)


def get_child(child_id: int | None) -> dict[str, Any] | None:
    if not child_id:
        return None
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM children WHERE id = ?", (child_id,)).fetchone()
        return row_to_dict(row)


def add_event(
    child_id: int,
    event_type: str,
    event_time: str,
    details: str = "",
    mood: str = "",
    intensity: int | None = None,
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO events (child_id, event_type, event_time, details, mood, intensity, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (child_id, event_type, event_time, details, mood, intensity, _now()),
        )
        return int(cur.lastrowid)


def get_events(child_id: int, limit: int = 100) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM events
            WHERE child_id = ?
            ORDER BY event_time DESC
            LIMIT ?
            """,
            (child_id, limit),
        ).fetchall()
        return rows_to_dicts(rows)


def get_today_logs(child_id: int) -> list[dict[str, Any]]:
    start = datetime.combine(date.today(), datetime.min.time()).isoformat()
    end = datetime.combine(date.today() + timedelta(days=1), datetime.min.time()).isoformat()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM events
            WHERE child_id = ? AND event_time >= ? AND event_time < ?
            ORDER BY event_time ASC
            """,
            (child_id, start, end),
        ).fetchall()
        return rows_to_dicts(rows)


def get_recent_logs(child_id: int, days: int = 7) -> list[dict[str, Any]]:
    since = (datetime.now() - timedelta(days=days)).isoformat()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM events
            WHERE child_id = ? AND event_time >= ?
            ORDER BY event_time DESC
            LIMIT 200
            """,
            (child_id, since),
        ).fetchall()
        return rows_to_dicts(rows)


def get_latest_event(child_id: int, event_types: list[str]) -> dict[str, Any] | None:
    placeholders = ",".join("?" for _ in event_types)
    with get_connection() as conn:
        row = conn.execute(
            f"""
            SELECT * FROM events
            WHERE child_id = ? AND event_type IN ({placeholders})
            ORDER BY event_time DESC
            LIMIT 1
            """,
            (child_id, *event_types),
        ).fetchone()
        return row_to_dict(row)


def get_latest_meal(child_id: int) -> dict[str, Any] | None:
    return get_latest_event(child_id, ["food"])


def get_latest_nap(child_id: int) -> dict[str, Any] | None:
    return get_latest_event(child_id, ["nap", "sleep"])


def get_latest_mood(child_id: int) -> dict[str, Any] | None:
    return get_latest_event(child_id, ["mood"])


def get_last_wake(child_id: int) -> dict[str, Any] | None:
    return get_latest_event(child_id, ["wake"])


def save_ai_question(child_id: int, question: str, answer: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO ai_questions (child_id, question, answer, created_at) VALUES (?, ?, ?, ?)",
            (child_id, question, answer, _now()),
        )
        return int(cur.lastrowid)


def save_feedback(question_id: int, child_id: int, feedback: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO ai_feedback (question_id, child_id, feedback, created_at) VALUES (?, ?, ?, ?)",
            (question_id, child_id, feedback, _now()),
        )
        return int(cur.lastrowid)


def get_feedback(child_id: int, limit: int = 50) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT f.*, q.question, q.answer
            FROM ai_feedback f
            JOIN ai_questions q ON q.id = f.question_id
            WHERE f.child_id = ?
            ORDER BY f.created_at DESC
            LIMIT ?
            """,
            (child_id, limit),
        ).fetchall()
        return rows_to_dicts(rows)


def get_patterns(child_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM child_patterns WHERE child_id = ? ORDER BY last_updated DESC",
            (child_id,),
        ).fetchall()
        return rows_to_dicts(rows)


def replace_patterns(child_id: int, patterns: list[dict[str, Any]]) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM child_patterns WHERE child_id = ?", (child_id,))
        for pattern in patterns:
            conn.execute(
                """
                INSERT INTO child_patterns (
                    child_id, pattern_type, pattern_summary, confidence, last_updated
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    child_id,
                    pattern.get("pattern_type", "routine"),
                    pattern.get("pattern_summary", ""),
                    str(pattern.get("confidence", "medium")),
                    _now(),
                ),
            )


def load_demo_data() -> int:
    children = get_children()
    existing = next((child for child in children if child["name"].lower() == "aarav"), None)
    child_id = existing["id"] if existing else create_child(
        {
            "name": "Aarav",
            "age": "3",
            "usual_wake_time": "7:00 AM",
            "usual_nap_time": "1:00 PM",
            "usual_bedtime": "8:00 PM",
            "known_triggers": "Skipped naps, long screen time, late lunch",
            "comfort_actions": "Milk, story time, dim lights, cuddles",
            "food_preferences": "Banana, milk, rice, yogurt",
            "notes": "Usually cheerful after outdoor play. Needs a quiet wind-down before nap.",
        }
    )

    today = date.today()
    demo_events = [
        ("wake", "07:00", "Woke up for the day", "", None),
        ("food", "08:00", "Ate banana and milk", "", None),
        ("activity", "10:00", "Outdoor play", "", None),
        ("food", "12:30", "Ate small lunch", "", None),
        ("nap", "13:00", "Skipped nap", "", None),
        ("mood", "15:30", "Cranky and clingy", "cranky", 4),
        ("activity", "16:00", "Calmed with milk and story time", "calm", 2),
    ]

    existing_today = get_today_logs(child_id)
    existing_keys = {(event["event_type"], event["details"]) for event in existing_today}
    for event_type, time_text, details, mood, intensity in demo_events:
        if (event_type, details) in existing_keys:
            continue
        event_dt = datetime.fromisoformat(f"{today.isoformat()}T{time_text}:00")
        add_event(child_id, event_type, event_dt.isoformat(timespec="seconds"), details, mood, intensity)

    if not get_patterns(child_id):
        replace_patterns(
            child_id,
            [
                {
                    "pattern_type": "sleep",
                    "pattern_summary": "Gets cranky when the usual nap window is skipped or delayed.",
                    "confidence": "medium",
                },
                {
                    "pattern_type": "comfort",
                    "pattern_summary": "Often calms with milk, story time, and a quieter environment.",
                    "confidence": "medium",
                },
                {
                    "pattern_type": "activity",
                    "pattern_summary": "Outdoor play appears to improve morning mood.",
                    "confidence": "early signal",
                },
            ],
        )
    return child_id
