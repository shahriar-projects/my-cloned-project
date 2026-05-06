"""
Module 8 Student Enrollment backend — refactored.

Architecture:
    DatabaseLayer   – owns the SQLite connection; every method runs a single
                      query and returns raw rows (dicts) or a success flag.
    EnrollmentService – contains all business logic: input validation,
                        enrollment-key matching, summary counting, snapshot
                        assembly, and JSON export.  Never touches SQL directly.

Run with:
    python enrollment_starter.py
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Configuration / constants
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).with_name("student_enrollment_practice.db")
SNAPSHOT_PATH = Path(__file__).with_name("student_enrollment_snapshot.json")

CURRENT_STUDENT = {
    "user_id": "u100",
    "name": "Maya Patel",
    "email": "maya.patel@example.edu",
}

STATUS_ENROLLED = "enrolled"
STATUS_UNENROLLED = "unenrolled"

AVAILABLE_COURSE_KEYS = [
    {
        "course_id": "MISY350",
        "course_name": "Python for Business Analytics",
        "instructor": "Dr. Rivera",
        "enrollment_key": "MISY350-SPRING",
    },
    {
        "course_id": "DATA210",
        "course_name": "Data Storytelling",
        "instructor": "Prof. Morgan",
        "enrollment_key": "DATA210-SPRING",
    },
    {
        "course_id": "WEB220",
        "course_name": "Web Apps With Streamlit",
        "instructor": "Dr. Chen",
        "enrollment_key": "WEB220-SPRING",
    },
]

SAMPLE_ENROLLMENTS = [
    ("u100", "maya.patel@example.edu", "MISY350", STATUS_ENROLLED),
    ("u100", "maya.patel@example.edu", "DATA210", STATUS_UNENROLLED),
    ("u101", "alex@example.edu", "MISY350", STATUS_ENROLLED),
    ("u102", "blair@example.edu", "WEB220", STATUS_ENROLLED),
]


# ---------------------------------------------------------------------------
# Database Layer
# ---------------------------------------------------------------------------

class DatabaseLayer:
    """Thin wrapper around SQLite.  Every public method runs one query."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path

    # -- connection helper --------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
        return [dict(row) for row in rows]

    # -- schema & seed ------------------------------------------------------

    def create_tables(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS courses (
                    course_id      TEXT PRIMARY KEY,
                    course_name    TEXT NOT NULL,
                    instructor     TEXT NOT NULL,
                    enrollment_key TEXT NOT NULL UNIQUE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS enrollments (
                    enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id       TEXT NOT NULL,
                    email         TEXT NOT NULL,
                    course_id     TEXT NOT NULL,
                    status        TEXT NOT NULL DEFAULT 'enrolled',
                    enrolled_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, course_id),
                    FOREIGN KEY(course_id) REFERENCES courses(course_id)
                )
                """
            )

    def seed_courses(self, courses: list[dict[str, str]]) -> None:
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT OR IGNORE INTO courses
                    (course_id, course_name, instructor, enrollment_key)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (c["course_id"], c["course_name"],
                     c["instructor"], c["enrollment_key"])
                    for c in courses
                ],
            )

    def seed_enrollments(
        self, rows: list[tuple[str, str, str, str]]
    ) -> None:
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT OR IGNORE INTO enrollments
                    (user_id, email, course_id, status)
                VALUES (?, ?, ?, ?)
                """,
                rows,
            )

    # -- course queries -----------------------------------------------------

    def fetch_all_courses(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT course_id, course_name, instructor, enrollment_key
                FROM courses
                ORDER BY course_id
                """
            ).fetchall()
        return self._rows_to_dicts(rows)

    def fetch_course_by_key(
        self, enrollment_key: str
    ) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT course_id, course_name, instructor, enrollment_key
                FROM courses
                WHERE enrollment_key = ?
                """,
                (enrollment_key,),
            ).fetchone()
        return dict(row) if row else None

    # -- enrollment queries -------------------------------------------------

    def fetch_enrollments(
        self, user_id: str, status: Optional[str] = None
    ) -> list[dict[str, Any]]:
        if status:
            sql = """
                SELECT e.enrollment_id, e.user_id, e.email, e.course_id,
                       c.course_name, c.instructor, e.status, e.enrolled_at
                FROM enrollments e
                JOIN courses c ON c.course_id = e.course_id
                WHERE e.user_id = ? AND e.status = ?
                ORDER BY c.course_id
            """
            params: tuple = (user_id, status)
        else:
            sql = """
                SELECT e.enrollment_id, e.user_id, e.email, e.course_id,
                       c.course_name, c.instructor, e.status, e.enrolled_at
                FROM enrollments e
                JOIN courses c ON c.course_id = e.course_id
                WHERE e.user_id = ?
                ORDER BY c.course_id
            """
            params = (user_id,)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return self._rows_to_dicts(rows)

    def fetch_student_course_record(
        self, user_id: str, course_id: str
    ) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT enrollment_id, user_id, email,
                       course_id, status, enrolled_at
                FROM enrollments
                WHERE user_id = ? AND course_id = ?
                """,
                (user_id, course_id),
            ).fetchone()
        return dict(row) if row else None

    def upsert_enrollment(
        self, user_id: str, email: str, course_id: str, status: str
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO enrollments (user_id, email, course_id, status)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, course_id)
                DO UPDATE SET
                    email       = excluded.email,
                    status      = excluded.status,
                    enrolled_at = CURRENT_TIMESTAMP
                """,
                (user_id, email, course_id, status),
            )

    def update_enrollment_status(
        self, user_id: str, course_id: str, new_status: str
    ) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE enrollments
                SET status = ?
                WHERE user_id = ? AND course_id = ?
                """,
                (new_status, user_id, course_id),
            )
        return cursor.rowcount > 0

    def fetch_all_enrollment_records(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT e.enrollment_id, e.user_id, e.email, e.course_id,
                       c.course_name, c.instructor, e.status, e.enrolled_at
                FROM enrollments e
                JOIN courses c ON c.course_id = e.course_id
                ORDER BY e.user_id, e.course_id
                """
            ).fetchall()
        return self._rows_to_dicts(rows)


# ---------------------------------------------------------------------------
# Service Layer
# ---------------------------------------------------------------------------

class EnrollmentService:
    """Business logic for enrollment operations.  Never runs SQL directly."""

    def __init__(self, db: DatabaseLayer) -> None:
        self.db = db

    # -- setup --------------------------------------------------------------

    def initialize_database(self) -> None:
        self.db.create_tables()
        self.db.seed_courses(AVAILABLE_COURSE_KEYS)
        self.db.seed_enrollments(SAMPLE_ENROLLMENTS)

    # -- read helpers -------------------------------------------------------

    def get_available_course_keys(self) -> list[dict[str, Any]]:
        return self.db.fetch_all_courses()

    def get_student_enrollments(
        self, user_id: str
    ) -> list[dict[str, Any]]:
        if not user_id:
            return []
        return self.db.fetch_enrollments(user_id, status=STATUS_ENROLLED)

    def get_student_enrollment_history(
        self, user_id: str
    ) -> list[dict[str, Any]]:
        if not user_id:
            return []
        return self.db.fetch_enrollments(user_id)

    # -- enrollment actions -------------------------------------------------

    def enroll_with_key(
        self, user_id: str, email: str, enrollment_key: str
    ) -> Optional[dict[str, Any]]:
        # --- validation (service concern) ---
        if not user_id or not email or "@" not in email:
            return None
        if not enrollment_key:
            return None

        key_upper = enrollment_key.strip().upper()

        # --- look up course ---
        course = self.db.fetch_course_by_key(key_upper)
        if not course:
            return None

        # --- perform enrollment (DB concern) ---
        self.db.upsert_enrollment(
            user_id, email, course["course_id"], STATUS_ENROLLED
        )
        return self.db.fetch_student_course_record(
            user_id, course["course_id"]
        )

    def soft_unenroll_student(
        self, user_id: str, course_id: str
    ) -> bool:
        if not user_id or not course_id:
            return False
        return self.db.update_enrollment_status(
            user_id, course_id, STATUS_UNENROLLED
        )

    # -- summary (service-level counting) -----------------------------------

    def get_student_summary(self, user_id: str) -> dict[str, int]:
        summary: dict[str, int] = {
            "total_records": 0,
            STATUS_ENROLLED: 0,
            STATUS_UNENROLLED: 0,
        }
        for record in self.get_student_enrollment_history(user_id):
            summary["total_records"] += 1
            status = record["status"]
            if status in summary:
                summary[status] += 1
        return summary

    # -- export (service-level orchestration) --------------------------------

    def export_database_snapshot(
        self, path: Path = SNAPSHOT_PATH
    ) -> None:
        snapshot = {
            "current_student": CURRENT_STUDENT,
            "available_course_keys": self.get_available_course_keys(),
            "enrollment_table": self.db.fetch_all_enrollment_records(),
        }
        path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def main() -> None:
    """Terminal runner — same behavior as the original starter."""
    db = DatabaseLayer(DB_PATH)
    service = EnrollmentService(db)

    service.initialize_database()

    user_id = CURRENT_STUDENT["user_id"]
    email = CURRENT_STUDENT["email"]

    print("Current student:")
    print(CURRENT_STUDENT)

    print("\nAvailable enrollment keys:")
    print(service.get_available_course_keys())

    print("\nInitial enrolled classes:")
    print(service.get_student_enrollments(user_id))

    print("\nStudent enters key DATA210-SPRING:")
    print(service.enroll_with_key(user_id, email, "DATA210-SPRING"))

    print("\nUpdated enrolled classes:")
    print(service.get_student_enrollments(user_id))

    print("\nStudent summary:")
    print(service.get_student_summary(user_id))

    service.export_database_snapshot()
    print(f"\nDatabase snapshot written to: {SNAPSHOT_PATH}")


if __name__ == "__main__":
    main()
