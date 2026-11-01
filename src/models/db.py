from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = os.getenv("DATABASE_PATH", "screening.db")


@contextmanager
def get_conn():
    """Thread-safe SQLite connection context manager."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # concurrent reads during writes
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS applicants (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL DEFAULT 'Unknown',
                email       TEXT    NOT NULL DEFAULT '',
                phone       TEXT    NOT NULL DEFAULT '',
                resume_text TEXT    NOT NULL,
                parsed_data TEXT    NOT NULL DEFAULT '{}',
                screening_score REAL,
                status      TEXT    NOT NULL DEFAULT 'screened',
                created_at  TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS interviews (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                applicant_id          INTEGER NOT NULL REFERENCES applicants(id),
                interview_data        TEXT    NOT NULL DEFAULT '{}',
                validation_results    TEXT    NOT NULL DEFAULT '{}',
                interview_score       REAL,
                evaluation_partial    INTEGER NOT NULL DEFAULT 0,
                evaluation_components TEXT    NOT NULL DEFAULT '{}',
                mcp_error             TEXT,
                created_at            TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS recommendations (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                applicant_id INTEGER NOT NULL REFERENCES applicants(id),
                interview_id INTEGER NOT NULL REFERENCES interviews(id),
                final_score  REAL,
                recommendation TEXT,
                reasoning    TEXT    NOT NULL DEFAULT '',
                created_at   TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT    NOT NULL,
                event     TEXT    NOT NULL,
                user_id   TEXT    NOT NULL DEFAULT 'unknown',
                data      TEXT    NOT NULL DEFAULT '{}'
            );
        """)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── applicants ──────────────────────────────────────────────────────────────

def insert_applicant(
    name: str,
    email: str,
    phone: str,
    resume_text: str,
    parsed_data: dict,
    screening_score,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO applicants
               (name, email, phone, resume_text, parsed_data, screening_score, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'screened', ?)""",
            (name, email, phone, resume_text, json.dumps(parsed_data), screening_score, _now()),
        )
        return cur.lastrowid


def get_applicant(applicant_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM applicants WHERE id = ?", (applicant_id,)
        ).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["parsed_data"] = json.loads(d["parsed_data"])
    return d


def update_applicant_status(applicant_id: int, status: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE applicants SET status = ? WHERE id = ?", (status, applicant_id)
        )


def list_applicants(status_filter: str | None = None) -> list[dict]:
    with get_conn() as conn:
        if status_filter:
            rows = conn.execute(
                "SELECT * FROM applicants WHERE status = ? ORDER BY id", (status_filter,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM applicants ORDER BY id"
            ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["parsed_data"] = json.loads(d["parsed_data"])
        result.append(d)
    return result


# ── interviews ───────────────────────────────────────────────────────────────

def insert_interview(
    applicant_id: int,
    interview_data: dict,
    validation_results: dict,
    interview_score,
    evaluation_partial: bool,
    evaluation_components: dict,
    mcp_error: str | None,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO interviews
               (applicant_id, interview_data, validation_results, interview_score,
                evaluation_partial, evaluation_components, mcp_error, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                applicant_id,
                json.dumps(interview_data),
                json.dumps(validation_results),
                interview_score,
                int(evaluation_partial),
                json.dumps(evaluation_components),
                mcp_error,
                _now(),
            ),
        )
        return cur.lastrowid


def get_interviews_for_applicant(applicant_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM interviews WHERE applicant_id = ? ORDER BY id",
            (applicant_id,),
        ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["interview_data"] = json.loads(d["interview_data"])
        d["validation_results"] = json.loads(d["validation_results"])
        d["evaluation_components"] = json.loads(d["evaluation_components"])
        d["evaluation_partial"] = bool(d["evaluation_partial"])
        result.append(d)
    return result


# ── recommendations ───────────────────────────────────────────────────────────

def insert_recommendation(
    applicant_id: int,
    interview_id: int,
    final_score,
    recommendation: str,
    reasoning: str,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO recommendations
               (applicant_id, interview_id, final_score, recommendation, reasoning, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (applicant_id, interview_id, final_score, recommendation, reasoning, _now()),
        )
        return cur.lastrowid


def get_recommendations_for_applicant(applicant_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM recommendations WHERE applicant_id = ? ORDER BY id",
            (applicant_id,),
        ).fetchall()
    return [dict(row) for row in rows]


# ── audit log ─────────────────────────────────────────────────────────────────

def log_audit(event: str, user_id: str, data: dict) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO audit_log (timestamp, event, user_id, data) VALUES (?, ?, ?, ?)",
            (_now(), event, user_id, json.dumps(data)),
        )


def get_audit_log(limit: int = 200) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["data"] = json.loads(d["data"])
        result.append(d)
    return result
