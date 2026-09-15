import sqlite3
import json
from datetime import datetime

DB_NAME = "stabil.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        mode TEXT,
        psi REAL,
        tremor REAL,
        error REAL,
        depth_error REAL,
        pressure REAL,
        trajectory TEXT,
        timestamp TEXT,
        reach_distance REAL,
        reach_error REAL,
        reach_violations INTEGER DEFAULT 0
    )
    """)

    # Safely migrate existing databases if columns missing
    for col, col_type in [("reach_distance", "REAL"), ("reach_error", "REAL"), ("reach_violations", "INTEGER DEFAULT 0")]:
        try:
            c.execute(f"ALTER TABLE sessions ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()


def save_session(user_id, mode, psi, tremor, error, depth_error, pressure, trajectory,
                 reach_distance=None, reach_error=None, reach_violations=0):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    INSERT INTO sessions
    (user_id, mode, psi, tremor, error, depth_error, pressure, trajectory, timestamp, reach_distance, reach_error, reach_violations)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        mode,
        psi,
        tremor,
        error,
        depth_error,
        pressure,
        json.dumps(trajectory),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        reach_distance,
        reach_error,
        reach_violations
    ))

    conn.commit()
    conn.close()


def get_all_sessions(user_id="default"):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
    SELECT * FROM sessions
    WHERE user_id=?
    ORDER BY id ASC
    """, (user_id,))

    rows = c.fetchall()
    conn.close()
    return rows


def get_last_session(user_id="default"):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
    SELECT * FROM sessions
    WHERE user_id=?
    ORDER BY id DESC
    LIMIT 1
    """, (user_id,))

    row = c.fetchone()
    conn.close()
    return row
