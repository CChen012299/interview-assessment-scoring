import json
import sqlite3
from contextlib import closing
from pathlib import Path
from uuid import uuid4

from src.models import (
    AssessmentDetailResponse,
    AssessmentList,
    AssessmentSummary,
    AssessmentWithSections,
    ClassList,
    ClassResponse,
    ClassSummary,
    QuestionAnswer,
    ScoringSection,
    SectionScoreResponse,
    SectionSummary,
    StudentSummary,
    SubmissionResponse,
    SubmissionResponseList,
)

_DB_PATH = Path(__file__).parent.parent / "data" / "assessments.db"
_SEED_PATH = Path(__file__).parent.parent / "data" / "seed.sql"


def _connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str | Path = _DB_PATH) -> None:
    seed_sql = _SEED_PATH.read_text()
    with closing(_connect(db_path)) as conn:
        conn.executescript(seed_sql)


def get_assessment_with_sections(
    assessment_id: str, db_path: str | Path = _DB_PATH
) -> AssessmentWithSections | None:
    with closing(_connect(db_path)) as conn:
        row = conn.execute(
            "SELECT id, name FROM assessments WHERE id = ?", (assessment_id,)
        ).fetchone()
        if row is None:
            return None

        section_rows = conn.execute(
            "SELECT id, name, weight FROM sections WHERE assessment_id = ? ORDER BY id",
            (assessment_id,),
        ).fetchall()

        sections = []
        for sec_row in section_rows:
            question_rows = conn.execute(
                "SELECT id, correct_answer FROM questions WHERE section_id = ? ORDER BY id",
                (sec_row["id"],),
            ).fetchall()
            sections.append(
                ScoringSection(
                    id=sec_row["id"],
                    name=sec_row["name"],
                    weight=sec_row["weight"],
                    questions=[
                        QuestionAnswer(id=q["id"], correct_answer=q["correct_answer"])
                        for q in question_rows
                    ],
                )
            )

        return AssessmentWithSections(id=row["id"], name=row["name"], sections=sections)


def save_submission(
    student_id: str,
    assessment_id: str,
    section_scores: list[SectionScoreResponse],
    overall_percentage: float,
    passed: bool,
    db_path: str | Path = _DB_PATH,
) -> str:
    section_scores_json = json.dumps([s.model_dump() for s in section_scores])
    with closing(_connect(db_path)) as conn:
        existing = conn.execute(
            "SELECT id FROM submissions WHERE student_id = ? AND assessment_id = ?",
            (student_id, assessment_id),
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE submissions SET section_scores = ?, overall_percentage = ?, passed = ?"
                " WHERE id = ?",
                (section_scores_json, overall_percentage, int(passed), existing["id"]),
            )
            conn.commit()
            return existing["id"]
        else:
            submission_id = f"sub-{uuid4().hex[:8]}"
            conn.execute(
                "INSERT INTO submissions"
                " (id, student_id, assessment_id, section_scores, overall_percentage, passed)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (submission_id, student_id, assessment_id,
                 section_scores_json, overall_percentage, int(passed)),
            )
            conn.commit()
            return submission_id


def get_submissions_for_student(
    student_id: str, db_path: str | Path = _DB_PATH
) -> SubmissionResponseList:
    with closing(_connect(db_path)) as conn:
        rows = conn.execute(
            "SELECT id, student_id, assessment_id, section_scores, overall_percentage, passed"
            " FROM submissions WHERE student_id = ?",
            (student_id,),
        ).fetchall()

    return SubmissionResponseList(responses=[_row_to_submission(row) for row in rows])


# A class's submissions. The JOIN on class_students keeps only students on the
# class roster, so submissions from anyone else are dropped. Each query that
# uses this appends its own filters ("AND ...") and then " ORDER BY sub.rowid".
#
# ORDER BY rowid only makes the result deterministic. save_submission keeps one
# row per student and assessment, but the schema does not enforce it; should
# duplicates exist, the dicts built from these rows keep the highest-rowid row,
# which may not be the one a later resubmission updates. The real fix is a
# UNIQUE index on (student_id, assessment_id).
_CLASS_SUBMISSIONS_SQL = (
    "SELECT sub.id, sub.student_id, sub.assessment_id, sub.section_scores,"
    " sub.overall_percentage, sub.passed"
    " FROM submissions sub"
    " JOIN class_students cs ON cs.student_id = sub.student_id"
    " WHERE cs.class_id = ?"
)


def get_class_submissions_for_assessment(
    class_id: str, assessment_id: str, db_path: str | Path = _DB_PATH
) -> dict[str, SubmissionResponse]:
    """Fetch the stored submissions of a class's students for one assessment.

    Only students on the class roster are included: the JOIN on
    ``class_students`` drops submissions from anyone else. Students who have
    not submitted are simply absent from the result.

    Args:
        class_id: Class whose roster to use.
        assessment_id: Assessment to fetch submissions for.
        db_path: SQLite database file.

    Returns:
        Submissions keyed by student id. Empty if nobody in the class has
        submitted (or the class or assessment does not exist).
    """
    with closing(_connect(db_path)) as conn:
        rows = conn.execute(
            _CLASS_SUBMISSIONS_SQL + " AND sub.assessment_id = ? ORDER BY sub.rowid",
            (class_id, assessment_id),
        ).fetchall()

    return {row["student_id"]: _row_to_submission(row) for row in rows}


def _row_to_submission(row: sqlite3.Row) -> SubmissionResponse:
    """Convert a ``submissions`` row into a SubmissionResponse.

    Args:
        row: A row with the columns id, student_id, assessment_id,
            section_scores (JSON text), overall_percentage and passed (0/1).

    Returns:
        The parsed submission.
    """
    return SubmissionResponse(
        submission_id=row["id"],
        student_id=row["student_id"],
        assessment_id=row["assessment_id"],
        section_scores=[
            SectionScoreResponse.model_validate(score)
            for score in json.loads(row["section_scores"])
        ],
        overall_percentage=row["overall_percentage"],
        passed=bool(row["passed"]),
    )


def get_classes(db_path: str | Path = _DB_PATH) -> ClassList:
    with closing(_connect(db_path)) as conn:
        rows = conn.execute("SELECT id, name FROM classes ORDER BY id").fetchall()
    return ClassList(
        classes=[ClassSummary(id=row["id"], name=row["name"]) for row in rows]
    )


def get_class_with_students(
    class_id: str, db_path: str | Path = _DB_PATH
) -> ClassResponse | None:
    with closing(_connect(db_path)) as conn:
        row = conn.execute(
            "SELECT id, name, teacher_name FROM classes WHERE id = ?", (class_id,)
        ).fetchone()
        if row is None:
            return None

        student_rows = conn.execute(
            "SELECT s.id, s.name FROM students s"
            " JOIN class_students cs ON s.id = cs.student_id"
            " WHERE cs.class_id = ? ORDER BY s.id",
            (class_id,),
        ).fetchall()

    return ClassResponse(
        id=row["id"],
        name=row["name"],
        teacher_name=row["teacher_name"],
        students=[StudentSummary(id=s["id"], name=s["name"]) for s in student_rows],
    )


def get_assessments(db_path: str | Path = _DB_PATH) -> AssessmentList:
    with closing(_connect(db_path)) as conn:
        rows = conn.execute("SELECT id, name FROM assessments ORDER BY id").fetchall()
    return AssessmentList(
        assessments=[AssessmentSummary(id=row["id"], name=row["name"]) for row in rows]
    )


def get_assessment_detail(
    assessment_id: str, db_path: str | Path = _DB_PATH
) -> AssessmentDetailResponse | None:
    with closing(_connect(db_path)) as conn:
        row = conn.execute(
            "SELECT id, name FROM assessments WHERE id = ?", (assessment_id,)
        ).fetchone()
        if row is None:
            return None

        section_rows = conn.execute(
            "SELECT id, name, weight FROM sections WHERE assessment_id = ? ORDER BY id",
            (assessment_id,),
        ).fetchall()

    return AssessmentDetailResponse(
        id=row["id"],
        name=row["name"],
        sections=[
            SectionSummary(id=s["id"], name=s["name"], weight=s["weight"])
            for s in section_rows
        ],
    )
