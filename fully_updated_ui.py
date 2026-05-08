from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

import streamlit as st

# -----------------------------
# Constants / Config
# -----------------------------

DB_PATH = Path(__file__).with_name("student_enrollment_practice.db")
SNAPSHOT_PATH = Path(__file__).with_name("student_enrollment_snapshot.json")

STATUS_ENROLLED = "enrolled"
STATUS_UNENROLLED = "unenrolled"

CURRENT_STUDENT = {
    "user_id": "u100",
    "name": "Maya Patel",
    "email": "maya.patel@example.edu",
}

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


# -----------------------------
# Database Layer
# -----------------------------

class EnrollmentDatabase:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def rows_to_dicts(self, rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
        return [dict(row) for row in rows]

    def create_tables(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS courses (
                    course_id TEXT PRIMARY KEY,
                    course_name TEXT NOT NULL,
                    instructor TEXT NOT NULL,
                    enrollment_key TEXT NOT NULL UNIQUE
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS enrollments (
                    enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    email TEXT NOT NULL,
                    course_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'enrolled',
                    enrolled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, course_id),
                    FOREIGN KEY(course_id) REFERENCES courses(course_id)
                )
                """
            )

    def seed_sample_data(self) -> None:
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO courses (
                    course_id, course_name, instructor, enrollment_key
                )
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        course["course_id"],
                        course["course_name"],
                        course["instructor"],
                        course["enrollment_key"],
                    )
                    for course in AVAILABLE_COURSE_KEYS
                ],
            )

            connection.executemany(
                """
                INSERT OR IGNORE INTO enrollments (
                    user_id, email, course_id, status
                )
                VALUES (?, ?, ?, ?)
                """,
                SAMPLE_ENROLLMENTS,
            )

    def get_available_course_keys(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT course_id, course_name, instructor, enrollment_key
                FROM courses
                ORDER BY course_id
                """
            ).fetchall()

        return self.rows_to_dicts(rows)

    def get_course_by_key(self, enrollment_key: str) -> Optional[dict[str, Any]]:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT course_id, course_name, instructor, enrollment_key
                FROM courses
                WHERE enrollment_key = ?
                """,
                (enrollment_key,),
            ).fetchone()

        return dict(row) if row else None

    def get_student_records(self, user_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    e.enrollment_id,
                    e.user_id,
                    e.email,
                    e.course_id,
                    c.course_name,
                    c.instructor,
                    e.status,
                    e.enrolled_at
                FROM enrollments e
                JOIN courses c ON c.course_id = e.course_id
                WHERE e.user_id = ?
                ORDER BY c.course_id
                """,
                (user_id,),
            ).fetchall()

        return self.rows_to_dicts(rows)

    def get_student_course_record(
        self,
        user_id: str,
        course_id: str,
    ) -> Optional[dict[str, Any]]:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT enrollment_id, user_id, email, course_id, status, enrolled_at
                FROM enrollments
                WHERE user_id = ? AND course_id = ?
                """,
                (user_id, course_id),
            ).fetchone()

        return dict(row) if row else None

    def save_enrollment(
        self,
        user_id: str,
        email: str,
        course_id: str,
        status: str,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO enrollments (user_id, email, course_id, status)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, course_id)
                DO UPDATE SET
                    email = excluded.email,
                    status = excluded.status,
                    enrolled_at = CURRENT_TIMESTAMP
                """,
                (user_id, email, course_id, status),
            )

    def update_enrollment_status(
        self,
        user_id: str,
        course_id: str,
        status: str,
    ) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE enrollments
                SET status = ?
                WHERE user_id = ? AND course_id = ?
                """,
                (status, user_id, course_id),
            )

        return cursor.rowcount > 0

    def get_all_enrollment_records(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    e.enrollment_id,
                    e.user_id,
                    e.email,
                    e.course_id,
                    c.course_name,
                    c.instructor,
                    e.status,
                    e.enrolled_at
                FROM enrollments e
                JOIN courses c ON c.course_id = e.course_id
                ORDER BY e.user_id, e.course_id
                """
            ).fetchall()

        return self.rows_to_dicts(rows)


# -----------------------------
# Service Layer
# -----------------------------

class EnrollmentService:
    def __init__(self, database: EnrollmentDatabase):
        self.database = database

    def clean_enrollment_key(self, enrollment_key: str) -> Optional[str]:
        if not enrollment_key:
            return None

        return enrollment_key.strip().upper()

    def get_available_course_keys(self) -> list[dict[str, Any]]:
        return self.database.get_available_course_keys()

    def get_student_enrollments(self, user_id: str) -> list[dict[str, Any]]:
        if not user_id:
            return []

        records = self.database.get_student_records(user_id)
        return [record for record in records if record["status"] == STATUS_ENROLLED]

    def get_student_enrollment_history(self, user_id: str) -> list[dict[str, Any]]:
        if not user_id:
            return []

        return self.database.get_student_records(user_id)

    def enroll_with_key(
        self,
        user_id: str,
        email: str,
        enrollment_key: str,
    ) -> Optional[dict[str, Any]]:
        if not user_id or not email or "@" not in email:
            return None

        clean_key = self.clean_enrollment_key(enrollment_key)

        if not clean_key:
            return None

        course = self.database.get_course_by_key(clean_key)

        if not course:
            return None

        self.database.save_enrollment(
            user_id,
            email,
            course["course_id"],
            STATUS_ENROLLED,
        )

        return self.database.get_student_course_record(
            user_id,
            course["course_id"],
        )

    def soft_unenroll_student(self, user_id: str, course_id: str) -> bool:
        if not user_id or not course_id:
            return False

        return self.database.update_enrollment_status(
            user_id,
            course_id,
            STATUS_UNENROLLED,
        )

    def get_student_summary(self, user_id: str) -> dict[str, int]:
        summary = {
            "total_records": 0,
            STATUS_ENROLLED: 0,
            STATUS_UNENROLLED: 0,
        }

        records = self.get_student_enrollment_history(user_id)

        for record in records:
            summary["total_records"] += 1
            status = record["status"]

            if status in summary:
                summary[status] += 1

        return summary

    def build_dashboard_data(self, user_id: str) -> dict[str, Any]:
        return {
            "enrolled_classes": self.get_student_enrollments(user_id),
            "enrollment_history": self.get_student_enrollment_history(user_id),
            "summary": self.get_student_summary(user_id),
        }


# -----------------------------
# Snapshot Export
# -----------------------------

class SnapshotExporter:
    def __init__(
        self,
        service: EnrollmentService,
        database: EnrollmentDatabase,
        snapshot_path: Path,
    ):
        self.service = service
        self.database = database
        self.snapshot_path = snapshot_path

    def build_snapshot(self, current_student: dict[str, str]) -> dict[str, Any]:
        return {
            "current_student": current_student,
            "available_course_keys": self.service.get_available_course_keys(),
            "enrollment_table": self.database.get_all_enrollment_records(),
        }

    def export_snapshot(self, current_student: dict[str, str]) -> None:
        snapshot = self.build_snapshot(current_student)
        self.snapshot_path.write_text(
            json.dumps(snapshot, indent=2),
            encoding="utf-8",
        )


# -----------------------------
# Streamlit UI Layer
# -----------------------------

class StudentEnrollmentDashboard:
    def __init__(self, service: EnrollmentService):
        self.service = service

    def setup_session_state(self) -> None:
        st.session_state.setdefault("role", "student")
        st.session_state.setdefault("page", "dashboard")
        st.session_state.setdefault("selected_class", None)
        st.session_state.setdefault("message", None)

    def show_message(self) -> None:
        message = st.session_state.get("message")

        if not message:
            return

        message_type, message_text = message

        if message_type == "success":
            st.success(message_text)
        elif message_type == "warning":
            st.warning(message_text)
        elif message_type == "error":
            st.error(message_text)

        st.session_state["message"] = None

    def show(self) -> None:
        self.setup_session_state()

        if st.session_state["role"] != "student":
            st.error("This app is only available for students.")
            return

        st.sidebar.title("Navigation")

        selected_page = st.sidebar.radio(
            "Choose a page",
            ["dashboard", "class"],
            index=0 if st.session_state["page"] == "dashboard" else 1,
        )

        st.session_state["page"] = selected_page

        if st.session_state["page"] == "dashboard":
            self.show_dashboard()
        elif st.session_state["page"] == "class":
            self.show_selected_class_page()

    def show_dashboard(self) -> None:
        student = CURRENT_STUDENT
        user_id = student["user_id"]
        email = student["email"]

        st.title("Student Dashboard")
        st.caption(f"Logged in as {student['name']} ({email})")

        self.show_message()

        dashboard_data = self.service.build_dashboard_data(user_id)
        summary = dashboard_data["summary"]
        enrolled_classes = dashboard_data["enrolled_classes"]
        enrollment_history = dashboard_data["enrollment_history"]

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Records", summary["total_records"])
        col2.metric("Enrolled", summary[STATUS_ENROLLED])
        col3.metric("Unenrolled", summary[STATUS_UNENROLLED])

        st.divider()

        st.subheader("Enroll in a Class")

        with st.form("enrollment_form"):
            enrollment_key = st.text_input("Enrollment Key")
            submitted = st.form_submit_button("Enroll")

        if submitted:
            result = self.service.enroll_with_key(
                user_id=user_id,
                email=email,
                enrollment_key=enrollment_key,
            )

            if result:
                st.session_state["message"] = (
                    "success",
                    f"Successfully enrolled in {result['course_id']}.",
                )
                st.rerun()
            else:
                st.error("Invalid enrollment key. Please try again.")

        st.divider()

        st.subheader("My Enrolled Classes")

        if enrolled_classes:
            st.dataframe(
                enrolled_classes,
                use_container_width=True,
                hide_index=True,
            )

            course_options = {
                f"{course['course_id']} - {course['course_name']}": course
                for course in enrolled_classes
            }

            selected_label = st.selectbox(
                "Choose a class",
                list(course_options.keys()),
            )

            selected_course = course_options[selected_label]

            col1, col2 = st.columns(2)

            with col1:
                if st.button("Go to Class"):
                    st.session_state["selected_class"] = selected_course
                    st.session_state["page"] = "class"
                    st.rerun()

            with col2:
                if st.button("Unenroll"):
                    success = self.service.soft_unenroll_student(
                        user_id=user_id,
                        course_id=selected_course["course_id"],
                    )

                    if success:
                        st.session_state["message"] = (
                            "success",
                            f"You have unenrolled from {selected_course['course_id']}.",
                        )
                        st.session_state["selected_class"] = None
                        st.rerun()
                    else:
                        st.error("Unable to unenroll from this class.")
        else:
            st.warning("You are not currently enrolled in any classes.")

        st.divider()

        st.subheader("Enrollment History")

        if enrollment_history:
            st.dataframe(
                enrollment_history,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No enrollment history found.")

    def show_selected_class_page(self) -> None:
        selected_class = st.session_state.get("selected_class")

        st.title("Selected Class")

        if not selected_class:
            st.warning("No class selected.")

            if st.button("Back to Dashboard"):
                st.session_state["page"] = "dashboard"
                st.rerun()

            return

        st.subheader(selected_class["course_name"])
        st.caption(f"Course ID: {selected_class['course_id']}")

        st.divider()

        col1, col2 = st.columns(2)
        col1.metric("Status", selected_class["status"])
        col2.metric("Instructor", selected_class["instructor"])

        st.container()
        st.write("### Class Information")
        st.write(f"**Course ID:** {selected_class['course_id']}")
        st.write(f"**Course Name:** {selected_class['course_name']}")
        st.write(f"**Instructor:** {selected_class['instructor']}")
        st.write(f"**Enrollment Status:** {selected_class['status']}")
        st.write(f"**Enrolled At:** {selected_class['enrolled_at']}")

        st.divider()

        if st.button("Back to Dashboard"):
            st.session_state["page"] = "dashboard"
            st.rerun()


# -----------------------------
# Main Runner
# -----------------------------

def main() -> None:
    database = EnrollmentDatabase(DB_PATH)
    database.create_tables()
    database.seed_sample_data()

    service = EnrollmentService(database)
    exporter = SnapshotExporter(service, database, SNAPSHOT_PATH)
    exporter.export_snapshot(CURRENT_STUDENT)

    dashboard = StudentEnrollmentDashboard(service)
    dashboard.show()


if __name__ == "__main__":
    main()