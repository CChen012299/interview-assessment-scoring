# Implementation plan: class summary

**Feature:** `GET /classes/{class_id}/summary` gives a teacher an at-a-glance triage view of
one class across every assessment: who failed (and on which sections), who has not
submitted what, which sections most of the class did not pass, and headline numbers per
assessment. Students with nothing to follow up are counted, not listed.

**Where:** repo `interview-assessment-scoring`, branch `akash`, Python service in `python/`.
Absolute path: `C:/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python`
(in Git Bash: `/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python`).

**Why it is built this way:** see `class-summary-decisions.md`. Decision IDs starting with
**S** refer to it, and IDs starting with **D** refer to `class-results-decisions.md`. You
do not need to read either file to execute this plan.

**Status: verified in memory, not yet in Docker (2026-10-12).** Written in plan mode, so
nothing was written to a scratch copy. Instead:
- Every **Find** block was applied in memory to the real source text and matched exactly
  once.
- The resulting code ran against the seed in an in-memory SQLite database, with a
  minimal stand-in for pydantic and FastAPI (neither is installed outside Docker).
- All 13 new tests passed, and the Phase 1, 2 and 4 Verify outputs below matched.
- Six deliberate bugs (Appendix B) were each caught by at least one test.
- No new line exceeds 92 characters, and there are no unused imports.

Real pydantic validation, FastAPI serialization and flake8 have **not** run yet. Each
phase's **Verify** step is the real check: if one fails, stop and report (rule 10).

---

## Context

The class results endpoint (`GET /classes/{class_id}/assessments/{assessment_id}/results`)
is complete but overwhelming: it lists every student with every section score for one
assessment. A teacher opening a class wants the opposite: only what needs action, across
all assessments, in priority order. This endpoint answers three questions, in order:

1. **Who needs me, and for what?** `failed` (reteach a student) and `not_submitted`
   (chase a student), each worst first.
2. **What did the whole class not get?** `sections_to_reteach`.
3. **How is each assessment going?** `assessments`: submitted, passed, average.

Room 12A (`class-001`) from the seed data returns:

```json
{
  "class_id": "class-001", "class_name": "Room 12A", "teacher_name": "Ms. Rivera",
  "total_students": 5,
  "passed_all_count": 1,
  "failed": [
    {"id": "student-003", "name": "Priya Patel", "assessments": [
      {"id": "assess-001", "name": "Grade 3 Reading", "overall_percentage": 0.7,
       "failed_sections": [{"id": "sec-002", "name": "Comprehension", "points_earned": 2,
                            "points_possible": 4, "percentage": 0.5, "passed": false}]}]},
    {"id": "student-004", "name": "Alex Thompson", "assessments": ["...Vocabulary 1/3..."]}
  ],
  "not_submitted": [
    {"id": "student-005", "name": "Sam Rivera", "assessments": [
      {"id": "assess-001", "name": "Grade 3 Reading"},
      {"id": "assess-002", "name": "Grade 3 Math"}]},
    {"id": "student-002", "name": "Jordan Williams", "assessments": ["...Math..."]},
    {"id": "student-003", "name": "Priya Patel", "assessments": ["...Math..."]},
    {"id": "student-004", "name": "Alex Thompson", "assessments": ["...Math..."]}
  ],
  "sections_to_reteach": [],
  "assessments": [
    {"id": "assess-001", "name": "Grade 3 Reading", "submitted_count": 4,
     "passed_count": 2, "average_overall_percentage": 0.85825},
    {"id": "assess-002", "name": "Grade 3 Math", "submitted_count": 1,
     "passed_count": 1, "average_overall_percentage": 1.0}
  ]
}
```

---

## Read this first: rules for executing this plan

1. Work inside `python/`. Every path below is relative to `python/` unless it starts with
   `../`. Shell state may reset between commands, so start every shell command with
   `cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" &&`.
   Give file tools absolute paths built from the absolute path above.
2. Do the phases in order. Finish a phase's **Verify** step before starting the next one.
3. Copy code **exactly**: names, order, comments, blank lines, docstrings. Do not rename,
   reorder, reformat, "simplify" or add anything.
4. Make every edit as an exact-text find-and-replace with an Edit tool, and **Read each
   file before editing it**. Each **Find** block appears exactly once in its file. Do not
   use `sed`, regular expressions or scripts to edit.
5. **Line endings.** Every existing file under `python/` except `src/scoring.py` has
   Windows line endings (CRLF: carriage return + line feed) in the working tree, because
   git's `core.autocrlf` is `true`. The **Find** blocks are shown with plain line breaks;
   an Edit tool matches them and keeps each file's endings. New files may get LF or CRLF;
   either is fine, because git normalizes endings on commit. If a **Find** block is
   reported as not found, stop and report it.
6. **Never edit or delete:** `tests/conftest.py`, `tests/test_api.py`,
   `tests/test_scoring.py`, `tests/test_class_results.py`,
   `tests/test_class_results_api.py`, `src/scoring.py`, `src/config.py`,
   `src/class_results.py`, `data/seed.sql`, `requirements.txt`, `Dockerfile`,
   `docker-compose.yml`, anything in `../csharp/`, `../NOTES.md`, `../NOTES.md.template`,
   the repo-root `../README.md`, and the existing files in `../docs/`. **Creating** the
   two new test files in `python/tests/` (Phases 5 and 7) is explicitly requested.
7. **Never commit or push.** Leave every change in the working tree; the user reviews and
   commits each phase.
8. Run the tests with:
   ```bash
   cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && docker compose run --rm --build test 2>&1 | tail -15
   ```
   - `--build` is required: the image copies `src/` and `tests/` at build time, so
     without it you would test stale code.
   - The last lines hold the failure summary and the final summary line, which is what
     the Verify steps check. Below, "run the tests" means this command.
   - **The exit code is always non-zero** because of the known failing test (rule 9), so
     judge every run by its printed output.
9. **Expected in every test run:** exactly one failing test,
   `tests/test_api.py::test_submit_returns_500_before_scoring_implemented` (stale by
   design, D23; do not fix, skip or delete it). Ignore any deprecation warnings.
10. If a **Verify** result differs from what the phase says, **stop**. Report the phase,
    the command and its full output. Do not improvise a fix.
11. Keep every line at 92 characters or fewer.
12. **The user's coding standards are already applied, with three deliberate
    exceptions.** Do not "fix" them:
    - Existing code gets no new docstrings or type hints (D24).
    - The new test files copy the provided tests' style exactly: no module docstrings,
      and no docstrings or type hints on test functions or their small helpers (D19).
    - The three over-long lines that already exist in `src/database.py` stay (Phase 8).
13. Code comments never use gendered pronouns for students: name the student, or
    rephrase.
14. Run commands in a Bash shell (Git Bash on Windows). The `python -c "..."` checks rely
    on Bash quoting.

---

## Phase overview

| Phase | What | Files | Tests after the phase |
|---|---|---|---|
| 0 | Preflight: confirm the baseline | none | 1 failed, 31 passed |
| 1 | Refactor: shared class-submissions SQL | `src/database.py` | 1 failed, 31 passed |
| 2 | Bulk queries | `src/database.py` | 1 failed, 31 passed |
| 3 | Response models | `src/models.py` | 1 failed, 31 passed |
| 4 | Pure summary module | `src/class_summary.py` (new) | 1 failed, 31 passed |
| 5 | Unit tests | `tests/test_class_summary.py` (new) | 1 failed, 38 passed |
| 6 | The route | `src/app.py` | 1 failed, 38 passed |
| 7 | API tests | `tests/test_class_summary_api.py` (new) | 1 failed, 44 passed |
| 8 | Lint and smoke test | none | unchanged |
| 9 | Document the endpoint | `README.md` (the one in `python/`) | unchanged |
| 10 | Final check and report | none | unchanged |

Each phase is one reviewable, behavior-coherent change, so the user can commit phase by
phase as before.

---

## Phase 0: Preflight

**Goal:** confirm the starting point before changing anything.

1. `git branch --show-current`. Expected: `akash`.
2. `git -C .. status --short python/src python/tests`. Expected: **no output**, meaning
   no uncommitted changes to source or tests. If anything is listed, stop and report.
   Other entries in a plain `git -C .. status --short` (the user's own edits to
   `NOTES.md`, `NOTES.md.template` or `python/README.md`, or uncommitted files in `docs/`)
   are fine. Leave them alone, and list them in the Phase 10 report.
3. Run the tests.

**Verify:** the summary line contains `1 failed, 31 passed`, and the failing test is
`test_submit_returns_500_before_scoring_implemented`.

---

## Phase 1: Refactor: shared class-submissions SQL

**Goal:** move the roster-JOIN SQL out of `get_class_submissions_for_assessment` into a
module constant that Phase 2's bulk query will share. **No behavior change.**

**Why:** the rule "only students on the roster count" is business logic living in SQL.
Two queries with two copies of it could drift apart: a later fix to one, such as the
duplicate-row fix the comment describes, would silently miss the other. A refactor-only
phase also gives the user a commit whose diff is easy to check: same SQL, new home.

**1.1** In `src/database.py`, **Find:**
```python
def get_class_submissions_for_assessment(
```
**Replace with:**
```python
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
```

**1.2** In `src/database.py`, **Find:**
```python
    with closing(_connect(db_path)) as conn:
        # ORDER BY rowid only makes the result deterministic. save_submission
        # keeps one row per student and assessment, but the schema does not
        # enforce it; should duplicates exist, the dict below keeps the
        # highest-rowid row, which may not be the one a later resubmission
        # updates. The real fix is a UNIQUE index on (student_id, assessment_id).
        rows = conn.execute(
            "SELECT sub.id, sub.student_id, sub.assessment_id, sub.section_scores,"
            " sub.overall_percentage, sub.passed"
            " FROM submissions sub"
            " JOIN class_students cs ON cs.student_id = sub.student_id"
            " WHERE cs.class_id = ? AND sub.assessment_id = ?"
            " ORDER BY sub.rowid",
            (class_id, assessment_id),
        ).fetchall()
```
**Replace with:**
```python
    with closing(_connect(db_path)) as conn:
        rows = conn.execute(
            _CLASS_SUBMISSIONS_SQL + " AND sub.assessment_id = ? ORDER BY sub.rowid",
            (class_id, assessment_id),
        ).fetchall()
```

**How it works:** Python joins adjacent string literals at compile time, so the
parenthesized constant is a single string. Concatenating the filter rebuilds exactly the
SQL that was there before. The `?` placeholders stay parameterized, so this is still safe
from SQL injection.

**Verify:**
1. The rebuilt SQL is character-for-character the old SQL:
   ```bash
   cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && docker compose run --rm --build test python -c "
   from src.database import _CLASS_SUBMISSIONS_SQL
   old = ('SELECT sub.id, sub.student_id, sub.assessment_id, sub.section_scores,'
          ' sub.overall_percentage, sub.passed'
          ' FROM submissions sub'
          ' JOIN class_students cs ON cs.student_id = sub.student_id'
          ' WHERE cs.class_id = ? AND sub.assessment_id = ?'
          ' ORDER BY sub.rowid')
   assert _CLASS_SUBMISSIONS_SQL + ' AND sub.assessment_id = ? ORDER BY sub.rowid' == old
   print('sql-unchanged')
   " 2>&1 | tail -1
   ```
   Expected: `sql-unchanged`.
2. Run the tests. Expected: `1 failed, 31 passed`. The results endpoint's API tests use
   this query, so they guard the refactor.

---

## Phase 2: Bulk queries

**Goal:** two new read functions that fetch everything the summary needs in a fixed number
of queries (S9).

**2.1** In `src/database.py`, **Find:**
```python
    return {row["student_id"]: _row_to_submission(row) for row in rows}


def _row_to_submission(row: sqlite3.Row) -> SubmissionResponse:
```
**Replace with:**
```python
    return {row["student_id"]: _row_to_submission(row) for row in rows}


def get_class_submissions(
    class_id: str, db_path: str | Path = _DB_PATH
) -> dict[str, dict[str, SubmissionResponse]]:
    """Fetch the stored submissions of a class's students for every assessment.

    The all-assessments counterpart of
    :func:`get_class_submissions_for_assessment`: one query, however many
    assessments exist. Only students on the class roster are included.

    Args:
        class_id: Class whose roster to use.
        db_path: SQLite database file.

    Returns:
        Submissions keyed by assessment id, then by student id. An assessment
        nobody in the class has submitted has no key. Empty if nobody in the
        class has submitted anything (or the class does not exist).
    """
    with closing(_connect(db_path)) as conn:
        rows = conn.execute(
            _CLASS_SUBMISSIONS_SQL + " ORDER BY sub.rowid", (class_id,)
        ).fetchall()

    submissions: dict[str, dict[str, SubmissionResponse]] = {}
    for row in rows:
        # setdefault returns the assessment's inner dict, creating it the first
        # time that assessment appears
        by_student_id = submissions.setdefault(row["assessment_id"], {})
        by_student_id[row["student_id"]] = _row_to_submission(row)
    return submissions


def _row_to_submission(row: sqlite3.Row) -> SubmissionResponse:
```

**2.2** In `src/database.py`, **Find:**
```python
            SectionSummary(id=s["id"], name=s["name"], weight=s["weight"])
            for s in section_rows
        ],
    )
```
**Replace with:**
```python
            SectionSummary(id=s["id"], name=s["name"], weight=s["weight"])
            for s in section_rows
        ],
    )


def get_all_assessment_details(
    db_path: str | Path = _DB_PATH,
) -> list[AssessmentDetailResponse]:
    """Fetch every assessment with its sections, in two queries.

    The whole-catalog counterpart of :func:`get_assessment_detail`: two
    queries however many assessments exist, instead of one per assessment.

    Args:
        db_path: SQLite database file.

    Returns:
        Every assessment ordered by id, each with its sections ordered by id
        (the orders :func:`get_assessments` and :func:`get_assessment_detail`
        use). An assessment without sections has an empty list. Empty if there
        are no assessments.
    """
    with closing(_connect(db_path)) as conn:
        assessment_rows = conn.execute(
            "SELECT id, name FROM assessments ORDER BY id"
        ).fetchall()
        section_rows = conn.execute(
            "SELECT id, assessment_id, name, weight FROM sections"
            " ORDER BY assessment_id, id"
        ).fetchall()

    # Group the sections by assessment in Python instead of querying once per
    # assessment
    sections_by_assessment_id: dict[str, list[SectionSummary]] = {}
    for row in section_rows:
        sections_by_assessment_id.setdefault(row["assessment_id"], []).append(
            SectionSummary(id=row["id"], name=row["name"], weight=row["weight"])
        )

    return [
        AssessmentDetailResponse(
            id=row["id"],
            name=row["name"],
            sections=sections_by_assessment_id.get(row["id"], []),
        )
        for row in assessment_rows
    ]
```

No new imports: `AssessmentDetailResponse`, `SectionSummary` and `SubmissionResponse` are
already imported.

**How it works:**
- `dict.setdefault(key, default)` returns the value for `key`, first inserting `default`
  if the key is missing. It builds a "dict of dicts" or "dict of lists" in one pass, with
  no `if key not in ...` branch.
- `ORDER BY assessment_id, id` sorts sections within each assessment by id, the same
  order `get_assessment_detail` returns (D15). Grouping preserves it.
- `.get(row["id"], [])` gives an assessment with no sections an empty list instead of a
  `KeyError`.
- The `db_path: str | Path` signature matches the neighboring functions (D24).

**Verify:**
1. Against a fresh copy of the seed, inside the container (`/tmp` there is discarded with
   the container):
   ```bash
   cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && docker compose run --rm --build test python -c "
   from src.database import init_db, get_all_assessment_details, get_class_submissions
   init_db('/tmp/check.db')
   print([(a.id, [s.id for s in a.sections]) for a in get_all_assessment_details('/tmp/check.db')])
   subs = get_class_submissions('class-003', '/tmp/check.db')
   print({a: sorted(s) for a, s in sorted(subs.items())})
   print(get_class_submissions('does-not-exist', '/tmp/check.db'))
   " 2>&1 | tail -3
   ```
   Expected:
   ```text
   [('assess-001', ['sec-001', 'sec-002']), ('assess-002', ['sec-003', 'sec-004'])]
   {'assess-001': ['student-006', 'student-007', 'student-009', 'student-010'], 'assess-002': ['student-009']}
   {}
   ```
2. Run the tests. Expected: `1 failed, 31 passed`.

---

## Phase 3: Response models

**Goal:** the response shape. These are new classes only; nothing existing changes.

**Why these shapes:**
- **Reuse over new fields (DRY).** `FailedAssessment.failed_sections` reuses
  `SectionScoreResponse` (S4). The not-submitted list reuses `AssessmentSummary` (id and
  name). `SectionToReteach` nests the existing `AssessmentSummary` and
  `SectionResultSummary` instead of copying their fields.
- **Small, focused models.** Each list gets its own small model rather than one large
  model full of optional fields. That is interface segregation applied to data.
- **Field order is the reading order.** Pydantic serializes fields in declaration order,
  so someone reading raw JSON sees the triage lists first.

**3.1** In `src/models.py`, **Find:**
```python
    summary: ClassResultsSummary
    students: list[StudentResult]
```
**Replace with:**
```python
    summary: ClassResultsSummary
    students: list[StudentResult]


class FailedAssessment(BaseModel):
    """An assessment a student failed, with the sections that failed.

    Attributes:
        id: Assessment identifier.
        name: Assessment display name.
        overall_percentage: The student's stored overall percentage (0.0 to 1.0).
        failed_sections: Only the sections the student did not pass, in
            assessment order. Empty when the overall score alone caused the fail.
    """

    id: str
    name: str
    overall_percentage: float
    failed_sections: list[SectionScoreResponse]


class StudentFailures(BaseModel):
    """A roster student who failed at least one assessment.

    Attributes:
        id: Student identifier.
        name: Student display name.
        assessments: The assessments the student failed, in catalog order.
    """

    id: str
    name: str
    assessments: list[FailedAssessment]


class StudentNotSubmitted(BaseModel):
    """A roster student who has not submitted at least one assessment.

    Attributes:
        id: Student identifier.
        name: Student display name.
        assessments: The assessments the student has not submitted, in catalog
            order.
    """

    id: str
    name: str
    assessments: list[AssessmentSummary]


class SectionToReteach(BaseModel):
    """A section most of the class did not pass, flagged for whole-class reteaching.

    Attributes:
        assessment: The assessment the section belongs to.
        section: The class's results on the section.
    """

    assessment: AssessmentSummary
    section: SectionResultSummary


class AssessmentOverview(BaseModel):
    """Headline numbers for one assessment in a class summary.

    Attributes:
        id: Assessment identifier.
        name: Assessment display name.
        submitted_count: Roster students with a submission.
        passed_count: Students whose submission passed.
        average_overall_percentage: Mean overall percentage across submitters,
            or None when nobody has submitted.
    """

    id: str
    name: str
    submitted_count: int
    passed_count: int
    average_overall_percentage: Optional[float]


class ClassSummaryResponse(BaseModel):
    """Response for ``GET /classes/{class_id}/summary``.

    A triage view across every assessment in the catalog: students with
    nothing to follow up are counted, not listed. Not to be confused with
    ``ClassSummary``, the id-and-name entry in the class list.

    Attributes:
        class_id: Class identifier.
        class_name: Class display name.
        teacher_name: Name of the class's teacher.
        total_students: Students on the class roster.
        passed_all_count: Roster students who passed every assessment. With no
            assessments in the catalog, every student counts.
        failed: Students who failed at least one assessment, furthest from
            passing first.
        not_submitted: Students who have not submitted at least one
            assessment, most not submitted first.
        sections_to_reteach: Sections to reteach to the whole class.
        assessments: Headline numbers for every assessment, in catalog order.
    """

    class_id: str
    class_name: str
    teacher_name: str
    total_students: int
    passed_all_count: int
    failed: list[StudentFailures]
    not_submitted: list[StudentNotSubmitted]
    sections_to_reteach: list[SectionToReteach]
    assessments: list[AssessmentOverview]
```

No new imports: `Optional`, `BaseModel` and every referenced model are already defined
above in the file.

**Verify:**
1. The models import and the field order is right:
   ```bash
   cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && docker compose run --rm --build test python -c "
   from src.models import ClassSummaryResponse
   print(list(ClassSummaryResponse.model_fields))
   " 2>&1 | tail -1
   ```
   Expected:
   ```text
   ['class_id', 'class_name', 'teacher_name', 'total_students', 'passed_all_count', 'failed', 'not_submitted', 'sections_to_reteach', 'assessments']
   ```
2. Run the tests. Expected: `1 failed, 31 passed`.

---

## Phase 4: The pure summary module

**Goal:** all the summary logic, in a module with no database or HTTP code (D12). It
mirrors `src/class_results.py` and can be unit-tested with hand-built objects.

**Structure (single responsibility per function):**

| Function | One job |
|---|---|
| `summarize_class` (public) | Coordinates: compute each assessment once, build the four lists, assemble the response |
| `needs_reteach` (public) | The reteach business rule (S6), public so its boundaries can be tested directly |
| `_assessment_results` | One assessment's class summary, via `class_results` (S8) |
| `_failed_students` / `_failed_assessment` | The `failed` list and its entries |
| `_not_submitted_students` | The `not_submitted` list |
| `_sections_to_reteach` | Applies `needs_reteach` to every section |
| `_overview` | Reduces a `ClassResultsSummary` to headline numbers |
| `_assessment_ref` | An assessment's id and name, as list entries reference it |

**Concepts used:**
- **`@dataclass(frozen=True)`** generates `__init__`, `__repr__` and `__eq__` from the
  annotated fields. `frozen=True` makes the attributes read-only after creation, so one
  helper can't quietly change data another helper reads.
  `_AssessmentResults` is private because it is only a hand-off between helpers.
- **Computing each assessment once.** `per_assessment` is built once and then read by
  every list builder, rather than having each list recompute the summaries.
- **Stable sorting.** `sorted()` never reorders equal items, and with `reverse=True` it
  still keeps equal items in input order. Since the roster arrives in id order, ties need
  no extra sort key.
- **Multiplying instead of dividing** (`needs_reteach`) can't divide by zero, and half of
  a whole number is exact in floating point, so "exactly half" hits the boundary
  predictably.

**4.1** Create `src/class_summary.py` with exactly this content:
```python
"""A class's at-a-glance summary across every assessment.

Pure functions that turn a class roster, every assessment's sections and the
class's stored submissions into a triage view for the teacher: who failed and
on which sections, who has not submitted what, which sections most of the class
did not pass, and headline numbers per assessment. Students with nothing to
follow up are counted, not listed. Nothing here touches the database or HTTP.

Every assessment in the catalog counts for every class, because the schema has
no record of which assessments a class was given. "Not submitted" therefore
also covers assessments a class was never assigned.

Per-assessment counts and averages come from :mod:`src.class_results`, so they
mean exactly what they mean on the class results endpoint.
"""

from dataclasses import dataclass

from src.class_results import build_student_results, summarize_class_results
from src.models import (
    AssessmentDetailResponse,
    AssessmentOverview,
    AssessmentSummary,
    ClassResponse,
    ClassResultsSummary,
    ClassSummaryResponse,
    FailedAssessment,
    SectionResultSummary,
    SectionToReteach,
    StudentFailures,
    StudentNotSubmitted,
    StudentSummary,
    SubmissionResponse,
)

# A section is flagged for whole-class reteaching when fewer than this share of
# the students who submitted it passed: most of the class did not get it.
RETEACH_PASS_SHARE = 0.5

# A section is only judged once at least this share of the roster has submitted,
# so a handful of early submissions cannot flag it for the whole class.
RETEACH_MIN_SUBMITTED_SHARE = 0.5


@dataclass(frozen=True)
class _AssessmentResults:
    """One assessment's data for the class, computed once and read by every list.

    Attributes:
        assessment: The assessment and its sections.
        submissions: The class's submissions for the assessment, keyed by
            student id.
        summary: Class-wide counts and averages, from ``summarize_class_results``.
    """

    assessment: AssessmentDetailResponse
    submissions: dict[str, SubmissionResponse]
    summary: ClassResultsSummary


def summarize_class(
    class_: ClassResponse,
    assessments: list[AssessmentDetailResponse],
    submissions_by_assessment_id: dict[str, dict[str, SubmissionResponse]],
) -> ClassSummaryResponse:
    """Build a class's summary across every assessment.

    Args:
        class_: The class and its roster. Students who tie in a list keep
            roster order.
        assessments: Every assessment with its sections, in catalog order.
        submissions_by_assessment_id: The class's stored submissions, keyed by
            assessment id and then student id. An assessment nobody has
            submitted may be missing from the outer dict.

    Returns:
        The class summary. ``failed`` lists the student furthest from passing
        first and ``not_submitted`` the student with the most assessments not
        submitted first; ``sections_to_reteach`` and ``assessments`` follow
        catalog order.
    """
    per_assessment = [
        _assessment_results(
            class_.students,
            assessment,
            submissions_by_assessment_id.get(assessment.id, {}),
        )
        for assessment in assessments
    ]
    failed = _failed_students(class_.students, per_assessment)
    not_submitted = _not_submitted_students(class_.students, per_assessment)
    # Everyone on neither list has passed every assessment
    followed_up_ids = {student.id for student in [*failed, *not_submitted]}

    return ClassSummaryResponse(
        class_id=class_.id,
        class_name=class_.name,
        teacher_name=class_.teacher_name,
        total_students=len(class_.students),
        passed_all_count=len(class_.students) - len(followed_up_ids),
        failed=failed,
        not_submitted=not_submitted,
        sections_to_reteach=_sections_to_reteach(len(class_.students), per_assessment),
        assessments=[_overview(results) for results in per_assessment],
    )


def needs_reteach(section: SectionResultSummary, total_students: int) -> bool:
    """Decide whether a section should be retaught to the whole class.

    A section is flagged when fewer than ``RETEACH_PASS_SHARE`` of the students
    who submitted it passed, but only once at least
    ``RETEACH_MIN_SUBMITTED_SHARE`` of the roster has submitted; before that
    there is too little evidence to judge the whole class. Exactly half passing
    is not flagged, and exactly half the roster submitting is enough to judge.

    Args:
        section: The class's results on the section.
        total_students: Students on the class roster.

    Returns:
        True if the section should be retaught to the whole class.
    """
    # Comparing against a multiplied share, rather than dividing to get a rate,
    # cannot divide by zero when nobody has submitted or the roster is empty.
    # Half of a whole number is exact in floating point, so "exactly half"
    # always lands on the boundary.
    enough_submitted = (
        section.submitted_count >= RETEACH_MIN_SUBMITTED_SHARE * total_students
    )
    most_did_not_pass = (
        section.passed_count < RETEACH_PASS_SHARE * section.submitted_count
    )
    return enough_submitted and most_did_not_pass


def _assessment_results(
    students: list[StudentSummary],
    assessment: AssessmentDetailResponse,
    submissions: dict[str, SubmissionResponse],
) -> _AssessmentResults:
    """Compute one assessment's class summary and keep it with its inputs.

    Args:
        students: The class roster.
        assessment: The assessment and its sections.
        submissions: The class's submissions for the assessment, keyed by
            student id.

    Returns:
        The assessment, its submissions and its class-wide summary.
    """
    summary = summarize_class_results(
        build_student_results(students, submissions), assessment.sections
    )
    return _AssessmentResults(
        assessment=assessment, submissions=submissions, summary=summary
    )


def _failed_students(
    students: list[StudentSummary], per_assessment: list[_AssessmentResults]
) -> list[StudentFailures]:
    """List the students who failed at least one assessment, worst first.

    Students are ordered by their lowest failing overall percentage, so the
    student furthest from passing comes first. Ties keep roster order.

    Args:
        students: The class roster, in roster order.
        per_assessment: Every assessment's results, in catalog order.

    Returns:
        One entry per student who failed at least one assessment, listing
        those assessments in catalog order.
    """
    entries: list[StudentFailures] = []
    for student in students:
        failed_assessments: list[FailedAssessment] = []
        for results in per_assessment:
            submission = results.submissions.get(student.id)
            # Failed means a stored submission with a failing stored verdict:
            # the same two facts StudentResult.status reads
            if submission is not None and not submission.passed:
                failed_assessments.append(
                    _failed_assessment(results.assessment, submission)
                )
        if failed_assessments:
            entries.append(
                StudentFailures(
                    id=student.id, name=student.name, assessments=failed_assessments
                )
            )
    # sorted() is stable: students with equal scores keep their roster order
    return sorted(
        entries,
        key=lambda entry: min(failed.overall_percentage for failed in entry.assessments),
    )


def _failed_assessment(
    assessment: AssessmentDetailResponse, submission: SubmissionResponse
) -> FailedAssessment:
    """Describe a failed assessment by the sections the student did not pass.

    Args:
        assessment: The assessment the submission is for.
        submission: The student's failed submission.

    Returns:
        The assessment, the student's overall percentage and only their failed
        sections, in the order the submission stores them. The list is empty
        when the overall score alone caused the fail.
    """
    return FailedAssessment(
        id=assessment.id,
        name=assessment.name,
        overall_percentage=submission.overall_percentage,
        failed_sections=[
            score for score in submission.section_scores if not score.passed
        ],
    )


def _not_submitted_students(
    students: list[StudentSummary], per_assessment: list[_AssessmentResults]
) -> list[StudentNotSubmitted]:
    """List the students who have not submitted every assessment.

    Students with the most assessments not submitted come first. Ties keep
    roster order.

    Args:
        students: The class roster, in roster order.
        per_assessment: Every assessment's results, in catalog order.

    Returns:
        One entry per student with at least one assessment not submitted,
        listing those assessments in catalog order.
    """
    entries: list[StudentNotSubmitted] = []
    for student in students:
        not_submitted = [
            _assessment_ref(results.assessment)
            for results in per_assessment
            if student.id not in results.submissions
        ]
        if not_submitted:
            entries.append(
                StudentNotSubmitted(
                    id=student.id, name=student.name, assessments=not_submitted
                )
            )
    # reverse=True puts the most first; Python's sort stays stable when
    # reversed, so ties still keep roster order
    return sorted(entries, key=lambda entry: len(entry.assessments), reverse=True)


def _sections_to_reteach(
    total_students: int, per_assessment: list[_AssessmentResults]
) -> list[SectionToReteach]:
    """List the sections to reteach to the whole class, in catalog order.

    Args:
        total_students: Students on the class roster.
        per_assessment: Every assessment's results, in catalog order.

    Returns:
        One entry per section that :func:`needs_reteach` flags, in assessment
        order and then section order.
    """
    return [
        SectionToReteach(
            assessment=_assessment_ref(results.assessment), section=section
        )
        for results in per_assessment
        for section in results.summary.sections
        if needs_reteach(section, total_students)
    ]


def _overview(results: _AssessmentResults) -> AssessmentOverview:
    """Reduce one assessment's class summary to its headline numbers.

    Args:
        results: The assessment's results.

    Returns:
        The assessment's submitted and passed counts and its average.
    """
    return AssessmentOverview(
        id=results.assessment.id,
        name=results.assessment.name,
        submitted_count=results.summary.submitted_count,
        passed_count=results.summary.passed_count,
        average_overall_percentage=results.summary.average_overall_percentage,
    )


def _assessment_ref(assessment: AssessmentDetailResponse) -> AssessmentSummary:
    """Reduce an assessment to the id and name that list entries refer to it by.

    Args:
        assessment: The assessment, with its sections.

    Returns:
        The assessment's id and name.
    """
    return AssessmentSummary(id=assessment.id, name=assessment.name)
```

**Verify:**
1. Wire the module to the real queries against a fresh seed (Room 12C):
   ```bash
   cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && docker compose run --rm --build test python -c "
   from src.database import init_db, get_class_with_students, get_all_assessment_details, get_class_submissions
   from src.class_summary import summarize_class
   init_db('/tmp/check.db')
   s = summarize_class(get_class_with_students('class-003', '/tmp/check.db'), get_all_assessment_details('/tmp/check.db'), get_class_submissions('class-003', '/tmp/check.db'))
   print([f.id for f in s.failed], [n.id for n in s.not_submitted])
   print([(r.assessment.id, r.section.name) for r in s.sections_to_reteach], s.passed_all_count)
   " 2>&1 | tail -2
   ```
   Expected:
   ```text
   ['student-007', 'student-009', 'student-006', 'student-010'] ['student-006', 'student-007', 'student-010']
   [('assess-001', 'Comprehension')] 0
   ```
2. Run the tests. Expected: `1 failed, 31 passed`.

---

## Phase 5: Unit tests for the summary module

**Goal:** pin the summary's core decisions with hand-built objects, with no database.

**Test data, modeled on Room 12C** plus Morgan (who has submitted nothing), with two
deliberate differences from the seed. Taylor passes Math, so one student has nothing to
follow up. Riley fails Math narrowly (83.3% overall, Word Problems 2/3), so one student
has failed two assessments with very different scores. The `failed` order then depends
on ranking by the *lowest* failing score: a mutation check found that, without this,
`max` in place of `min` passed every test. A failing
submission from `student-999`, who is not on the roster, must be ignored everywhere. If
it weren't, Reading Vocabulary would become 2 of 5 passed and be flagged, so the reteach
test also pins this.

| Test | Pins |
|---|---|
| `test_failed_lists_students_worst_first_with_only_their_failed_sections` | S4, S5; a student failing two assessments; the outsider ignored |
| `test_not_submitted_lists_students_with_the_most_not_submitted_first` | S5, including roster order on ties |
| `test_students_with_nothing_to_follow_up_are_counted_not_listed` | S7 |
| `test_sections_to_reteach_flags_sections_fewer_than_half_passed` | S6; exactly half passing is not flagged |
| `test_needs_reteach_judges_only_once_half_the_roster_has_submitted` | S6's guard at its exact boundary |
| `test_assessments_give_headline_numbers_for_every_assessment` | S8; averages exclude non-submitters and the outsider |
| `test_summary_with_no_assessments_has_nothing_to_follow_up` | Degenerate data: an empty catalog |

**5.1** Create `tests/test_class_summary.py` with exactly this content:
```python
import pytest
from src.class_summary import needs_reteach, summarize_class
from src.config import MASTERY_THRESHOLD
from src.models import (
    AssessmentDetailResponse,
    ClassResponse,
    SectionResultSummary,
    SectionScoreResponse,
    SectionSummary,
    StudentSummary,
    SubmissionResponse,
)

READING = AssessmentDetailResponse(
    id="assess-001",
    name="Grade 3 Reading",
    sections=[
        SectionSummary(id="sec-001", name="Vocabulary", weight=0.4),
        SectionSummary(id="sec-002", name="Comprehension", weight=0.6),
    ],
)
MATH = AssessmentDetailResponse(
    id="assess-002",
    name="Grade 3 Math",
    sections=[
        SectionSummary(id="sec-003", name="Computation", weight=0.5),
        SectionSummary(id="sec-004", name="Word Problems", weight=0.5),
    ],
)
ASSESSMENTS = [READING, MATH]

# Modeled on Room 12C in the seed data, plus Morgan, who has submitted nothing.
# Unlike the seed, Taylor passes Math (so one student has nothing to follow up)
# and Riley fails it (so one student has failed two assessments).
CLASS = ClassResponse(
    id="class-003",
    name="Room 12C",
    teacher_name="Ms. Johnson",
    students=[
        StudentSummary(id="student-006", name="Casey Kim"),
        StudentSummary(id="student-007", name="Riley Johnson"),
        StudentSummary(id="student-008", name="Morgan Davis"),
        StudentSummary(id="student-009", name="Taylor Brown"),
        StudentSummary(id="student-010", name="Jamie Lee"),
    ],
)


def _section_score(section, earned, possible):
    return SectionScoreResponse(
        id=section.id,
        name=section.name,
        points_earned=earned,
        points_possible=possible,
        percentage=earned / possible,
        passed=earned / possible >= MASTERY_THRESHOLD,
    )


def _submission(student_id, assessment, points, overall, passed):
    # points holds (points_earned, points_possible) for each section, in order
    return SubmissionResponse(
        submission_id=f"sub-{student_id}-{assessment.id}",
        student_id=student_id,
        assessment_id=assessment.id,
        section_scores=[
            _section_score(section, *section_points)
            for section, section_points in zip(assessment.sections, points)
        ],
        overall_percentage=overall,
        passed=passed,
    )


SUBMISSIONS = {
    "assess-001": {
        # vocab 2/3, comp 3/4 -> 0.4*0.667 + 0.6*0.75 = 0.717, fails both sections
        "student-006": _submission(
            "student-006", READING, [(2, 3), (3, 4)], overall=0.717, passed=False
        ),
        # vocab 0/3, comp 1/4 -> 0.4*0.0 + 0.6*0.25 = 0.15, fails both sections
        "student-007": _submission(
            "student-007", READING, [(0, 3), (1, 4)], overall=0.15, passed=False
        ),
        # vocab 3/3, comp 4/4 -> 1.0, passed
        "student-009": _submission(
            "student-009", READING, [(3, 3), (4, 4)], overall=1.0, passed=True
        ),
        # vocab 3/3, comp 3/4 -> 0.4*1.0 + 0.6*0.75 = 0.85, fails Comprehension only
        "student-010": _submission(
            "student-010", READING, [(3, 3), (3, 4)], overall=0.85, passed=False
        ),
        # Not on the roster, so every list and count must ignore it
        "student-999": _submission(
            "student-999", READING, [(0, 3), (0, 4)], overall=0.0, passed=False
        ),
    },
    "assess-002": {
        # computation 3/3, word problems 2/3 -> 0.5*1.0 + 0.5*0.667 = 0.833, which
        # clears 80% overall but fails Word Problems
        "student-007": _submission(
            "student-007", MATH, [(3, 3), (2, 3)], overall=0.833, passed=False
        ),
        # computation 3/3, word problems 3/3 -> 1.0, passed
        "student-009": _submission(
            "student-009", MATH, [(3, 3), (3, 3)], overall=1.0, passed=True
        ),
    },
}


def test_failed_lists_students_worst_first_with_only_their_failed_sections():
    summary = summarize_class(CLASS, ASSESSMENTS, SUBMISSIONS)
    # Lowest failing overall first: Riley 0.15, Casey 0.717, Jamie 0.85. Riley
    # ranks by Reading (0.15), not by the near-miss Math (0.833), which would put
    # Riley between Casey and Jamie. The outsider's 0.0 is ignored.
    assert [s.id for s in summary.failed] == ["student-007", "student-006", "student-010"]
    riley = summary.failed[0]
    assert [a.id for a in riley.assessments] == ["assess-001", "assess-002"]
    jamie_reading = summary.failed[2].assessments[0]
    assert jamie_reading.overall_percentage == pytest.approx(0.85)
    # Jamie passed Vocabulary, so only Comprehension is listed
    assert [s.name for s in jamie_reading.failed_sections] == ["Comprehension"]


def test_not_submitted_lists_students_with_the_most_not_submitted_first():
    summary = summarize_class(CLASS, ASSESSMENTS, SUBMISSIONS)
    # Morgan has submitted neither assessment; Casey and Jamie tie on one each,
    # so they keep roster order
    assert [(s.id, [a.id for a in s.assessments]) for s in summary.not_submitted] == [
        ("student-008", ["assess-001", "assess-002"]),
        ("student-006", ["assess-002"]),
        ("student-010", ["assess-002"]),
    ]


def test_students_with_nothing_to_follow_up_are_counted_not_listed():
    summary = summarize_class(CLASS, ASSESSMENTS, SUBMISSIONS)
    # Taylor passed both assessments
    listed = {s.id for s in summary.failed} | {s.id for s in summary.not_submitted}
    assert "student-009" not in listed
    assert summary.total_students == 5
    assert summary.passed_all_count == 1


def test_sections_to_reteach_flags_sections_fewer_than_half_passed():
    summary = summarize_class(CLASS, ASSESSMENTS, SUBMISSIONS)
    # Reading, 4 of 5 submitted (the outsider is ignored):
    #   Comprehension: 1 of 4 passed -> flagged
    #   Vocabulary: 2 of 4 passed, exactly half -> not flagged
    # Math, 2 of 5 submitted: under half the roster, so not judged
    assert [(r.assessment.id, r.section.id) for r in summary.sections_to_reteach] == [
        ("assess-001", "sec-002")
    ]
    assert summary.sections_to_reteach[0].section.passed_count == 1


def test_needs_reteach_judges_only_once_half_the_roster_has_submitted():
    # 0 of 2 submitters passed, so most of them did not pass
    section = SectionResultSummary(
        id="sec-001",
        name="Vocabulary",
        weight=0.4,
        submitted_count=2,
        passed_count=0,
        average_percentage=0.25,
    )
    # 2 of 5 is under half the roster: too few submissions to judge the class
    assert needs_reteach(section, total_students=5) is False
    # 2 of 4 is exactly half the roster: enough to judge
    assert needs_reteach(section, total_students=4) is True


def test_assessments_give_headline_numbers_for_every_assessment():
    summary = summarize_class(CLASS, ASSESSMENTS, SUBMISSIONS)
    assert [a.id for a in summary.assessments] == ["assess-001", "assess-002"]
    reading = summary.assessments[0]
    # (0.717 + 0.15 + 1.0 + 0.85) / 4 = 0.679; the outsider is ignored
    assert reading.submitted_count == 4
    assert reading.passed_count == 1
    assert reading.average_overall_percentage == pytest.approx(0.679, abs=0.001)
    math = summary.assessments[1]
    # (0.833 + 1.0) / 2 = 0.917
    assert math.submitted_count == 2
    assert math.passed_count == 1
    assert math.average_overall_percentage == pytest.approx(0.917, abs=0.001)


def test_summary_with_no_assessments_has_nothing_to_follow_up():
    summary = summarize_class(CLASS, [], {})
    assert summary.failed == []
    assert summary.not_submitted == []
    assert summary.sections_to_reteach == []
    assert summary.assessments == []
    # Vacuously, every student has passed every assessment
    assert summary.passed_all_count == 5
```

**Verify:** run the tests. Expected: `1 failed, 38 passed`.

---

## Phase 6: The route

**Goal:** expose the module over HTTP. The route only fetches data and handles the 404;
`summarize_class` does the shaping. This is the same layering as `get_class_results`
(D12).

**6.1** In `src/app.py`, **Find:**
```python
from src.class_results import build_student_results, summarize_class_results
```
**Replace with:**
```python
from src.class_results import build_student_results, summarize_class_results
from src.class_summary import summarize_class
```

**6.2** In `src/app.py`, **Find:**
```python
from src.database import (
    get_assessment_detail,
```
**Replace with:**
```python
from src.database import (
    get_all_assessment_details,
    get_assessment_detail,
```

**6.3** In `src/app.py`, **Find:**
```python
    get_class_submissions_for_assessment,
```
**Replace with:**
```python
    get_class_submissions,
    get_class_submissions_for_assessment,
```

**6.4** In `src/app.py`, **Find:**
```python
    ClassSummary,
    SectionScoreResponse,
```
**Replace with:**
```python
    ClassSummary,
    ClassSummaryResponse,
    SectionScoreResponse,
```

**6.5** In `src/app.py`, **Find:**
```python
        summary=summarize_class_results(student_results, assessment.sections),
        students=student_results,
    )
```
**Replace with:**
```python
        summary=summarize_class_results(student_results, assessment.sections),
        students=student_results,
    )


# \f in the docstring: see the note above get_class_results.
@app.get("/classes/{class_id}/summary")
def get_class_summary(class_id: str) -> ClassSummaryResponse:
    """Return a class's at-a-glance summary across every assessment.

    Lists only the students who need follow-up: those who failed an assessment
    (with the sections they failed) and those who have not submitted one. Also
    flags sections most of the class did not pass, and gives each assessment's
    headline numbers. Every assessment counts for every class.
    \f
    Args:
        class_id: Class to summarize.

    Returns:
        The class summary.

    Raises:
        HTTPException: 404 if the class does not exist.
    """
    class_ = get_class_with_students(class_id, _DB_PATH)
    if class_ is None:
        raise HTTPException(status_code=404, detail="Class not found")

    return summarize_class(
        class_,
        get_all_assessment_details(_DB_PATH),
        get_class_submissions(class_id, _DB_PATH),
    )
```

**How it works:**
- The new imports keep the existing alphabetical order within each `import (...)` list.
- The return annotation `-> ClassSummaryResponse` is also FastAPI's response model, so
  `/docs` documents the shape.
- The 404 reuses the existing `"Class not found"` message (D14).
- `_DB_PATH` is read when the request arrives, which is what lets the `test_client`
  fixture point it at a temporary database.

**Verify:**
1. Call the route in-process against a fresh seed. Setting `_DB_PATH` first, as the
   `test_client` fixture does, keeps the host's `data/assessments.db` untouched:
   ```bash
   cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && docker compose run --rm --build test python -c "
   import src.app as app_module
   app_module._DB_PATH = '/tmp/check.db'
   from fastapi.testclient import TestClient
   with TestClient(app_module.app) as client:
       r = client.get('/classes/class-002/summary')
       print(r.status_code, [s['id'] for s in r.json()['failed']], client.get('/classes/nope/summary').status_code)
   " 2>&1 | tail -1
   ```
   Expected: `200 ['student-007', 'student-006', 'student-004'] 404`.
2. Run the tests. Expected: `1 failed, 38 passed`.

---

## Phase 7: API tests for the route

**Goal:** pin the wiring against the real seed data, including one submit-then-read
end-to-end test (scoring → storage → bulk queries → summary → JSON).

| Test | Class | Pins |
|---|---|---|
| `..._returns_404_for_unknown_class` | none | D14 |
| `..._lists_failed_students_worst_first` | 12B | S4, S5; not submitted is not failed |
| `..._lists_not_submitted_for_every_assessment` | 12A | **S2**: Math counts for everyone; S7 |
| `..._flags_sections_fewer_than_half_passed` | 12C | S6: one flagged, one at exactly half, one below the guard |
| `..._gives_headline_numbers_per_assessment` | 12B | S8; an assessment nobody took has a `null` average |
| `..._reflects_a_new_submission` | 12A | End to end |

**7.1** Create `tests/test_class_summary_api.py` with exactly this content:
```python
import pytest


def test_get_class_summary_returns_404_for_unknown_class(test_client):
    response = test_client.get("/classes/does-not-exist/summary")
    assert response.status_code == 404
    assert response.json()["detail"] == "Class not found"


def test_get_class_summary_lists_failed_students_worst_first(test_client):
    # Room 12B. Nobody in it has taken Grade 3 Math, so nobody has failed it
    response = test_client.get("/classes/class-002/summary")
    assert response.status_code == 200
    failed = response.json()["failed"]
    assert [s["id"] for s in failed] == [
        "student-007",  # Riley Johnson, 15%
        "student-006",  # Casey Kim, 71.7%
        "student-004",  # Alex Thompson, 73.3%
    ]
    alex = failed[2]
    assert [a["id"] for a in alex["assessments"]] == ["assess-001"]
    # Alex passed Comprehension, so only Vocabulary (1/3) is listed
    failed_sections = alex["assessments"][0]["failed_sections"]
    assert [s["name"] for s in failed_sections] == ["Vocabulary"]
    assert failed_sections[0]["points_earned"] == 1


def test_get_class_summary_lists_not_submitted_for_every_assessment(test_client):
    # Room 12A. Every assessment counts for every class, so Grade 3 Math, which
    # only Maya has taken, is listed for everyone else
    response = test_client.get("/classes/class-001/summary")
    assert response.status_code == 200
    not_submitted = response.json()["not_submitted"]
    assert [(s["id"], [a["id"] for a in s["assessments"]]) for s in not_submitted] == [
        ("student-005", ["assess-001", "assess-002"]),  # Sam Rivera
        ("student-002", ["assess-002"]),                # Jordan Williams
        ("student-003", ["assess-002"]),                # Priya Patel
        ("student-004", ["assess-002"]),                # Alex Thompson
    ]
    # Maya passed both assessments, so Maya is counted, not listed
    assert response.json()["passed_all_count"] == 1


def test_get_class_summary_flags_sections_fewer_than_half_passed(test_client):
    # Room 12C, 4 students:
    #   Reading Comprehension: 1 of 4 passed -> flagged
    #   Reading Vocabulary: 2 of 4 passed, exactly half -> not flagged
    #   Math: only Taylor has submitted (1 of 4, under half the roster), so it
    #   is not judged, even though 0 of 1 passed
    response = test_client.get("/classes/class-003/summary")
    assert response.status_code == 200
    flagged = response.json()["sections_to_reteach"]
    assert [(r["assessment"]["id"], r["section"]["name"]) for r in flagged] == [
        ("assess-001", "Comprehension")
    ]
    # (0.75 + 0.25 + 1.0 + 0.75) / 4 = 0.6875
    section = flagged[0]["section"]
    assert section["submitted_count"] == 4
    assert section["passed_count"] == 1
    assert section["average_percentage"] == pytest.approx(0.6875)


def test_get_class_summary_gives_headline_numbers_per_assessment(test_client):
    # Room 12B: 3 of 5 took Reading and none passed; nobody has taken Math
    response = test_client.get("/classes/class-002/summary")
    assert response.status_code == 200
    reading, math = response.json()["assessments"]
    assert reading["id"] == "assess-001"
    assert reading["submitted_count"] == 3
    assert reading["passed_count"] == 0
    # (0.733 + 0.717 + 0.15) / 3 = 0.533
    assert reading["average_overall_percentage"] == pytest.approx(0.533, abs=0.001)
    assert math["id"] == "assess-002"
    assert math["submitted_count"] == 0
    assert math["average_overall_percentage"] is None


def test_get_class_summary_reflects_a_new_submission(test_client):
    # End to end: Sam answers only the Vocabulary questions, so the submission
    # scores 0.4*1.0 + 0.6*0.0 = 0.4 and fails Comprehension
    submit = test_client.post(
        "/assessments/assess-001/submit",
        json={
            "student_id": "student-005",
            "answers": {"q-001": "author", "q-002": "setting", "q-003": "plot"},
        },
    )
    assert submit.status_code == 200
    response = test_client.get("/classes/class-001/summary")
    assert response.status_code == 200
    data = response.json()
    # Sam (0.4) is now furthest from passing, ahead of Priya (0.7) and Alex (0.733)
    assert [s["id"] for s in data["failed"]] == [
        "student-005", "student-003", "student-004"
    ]
    sam_reading = data["failed"][0]["assessments"][0]
    assert sam_reading["overall_percentage"] == pytest.approx(0.4)
    assert [s["name"] for s in sam_reading["failed_sections"]] == ["Comprehension"]
    sam = next(s for s in data["not_submitted"] if s["id"] == "student-005")
    assert [a["id"] for a in sam["assessments"]] == ["assess-002"]
```

**Verify:** run the tests. Expected: `1 failed, 44 passed`.

---

## Phase 8: Lint and smoke test

**8.1 flake8** (a PEP 8 style checker; it is not in `requirements.txt`, so it is installed
inside the throwaway container) on the new and changed files:
```bash
cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && docker compose run --rm --build test sh -c "pip install -q --root-user-action=ignore --disable-pip-version-check flake8 && flake8 --max-line-length 92 src/app.py src/class_summary.py src/models.py tests/test_class_summary.py tests/test_class_summary_api.py && echo flake8-clean" 2>&1 | tail -5
```
Expected last line: `flake8-clean`.

Then `src/database.py` on its own:
```bash
cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && docker compose run --rm --build test sh -c "pip install -q --root-user-action=ignore --disable-pip-version-check flake8 && flake8 --max-line-length 92 src/database.py" 2>&1 | tail -5
```
Expected: exactly these three pre-existing errors (E501 means "line too long"). Their line
numbers don't change, because every edit in this plan is below line 118. Any other error
means a mistake in Phase 1 or 2.
```text
src/database.py:94:93: E501 line too long (95 > 92 characters)
src/database.py:104:93: E501 line too long (94 > 92 characters)
src/database.py:118:93: E501 line too long (94 > 92 characters)
```

**8.2 Smoke test against a running server.** This step is optional. Leave the user's
environment the way you found it.

First, check whether the API is already running:
```bash
cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && docker compose ps --status running api
```
- **Case A: a container named like `python-api-1` is listed.** The user is running the
  API. **Skip the rest of 8.2**: do not restart, rebuild or stop it. In the Phase 10
  report, write: "Smoke test skipped: the API container was already running. Run
  `docker compose up --build -d api` to load the new code."
- **Case B: only the header line is listed.** Start the API, test it, then stop and
  remove only the container you started:
  ```bash
  cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && docker compose up --build -d api
  curl -s --retry 10 --retry-all-errors --retry-delay 1 http://localhost:8000/classes/class-002/summary | python -c "import json, sys; d = json.load(sys.stdin); print([s['id'] for s in d['failed']], [(r['assessment']['id'], r['section']['name']) for r in d['sections_to_reteach']], d['passed_all_count'])"
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/classes/does-not-exist/summary
  cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && docker compose rm -sf api
  ```
  Expected:
  ```text
  ['student-007', 'student-006', 'student-004'] [('assess-001', 'Vocabulary'), ('assess-001', 'Comprehension')] 0
  404
  ```
  The running API uses the persistent `data/assessments.db`, which may hold earlier
  manual submissions. If the first line differs, report the output rather than changing
  anything.

---

## Phase 9: Document the endpoint

**9.1** In `README.md` (the one in `python/`), **Find:**
```markdown
nobody has. Returns 404 if the class or the assessment does not exist.
```
**Replace with:**
````markdown
nobody has. Returns 404 if the class or the assessment does not exist.

### Get a class's summary

```bash
curl http://localhost:8000/classes/class-001/summary
```

A short triage view across every assessment. `failed` lists the students who failed an
assessment, furthest from passing first, with only the sections they failed.
`not_submitted` lists the students who have not submitted an assessment, most first.
`sections_to_reteach` flags sections that fewer than half of the submitters passed, once
at least half the class has submitted. `assessments` gives each assessment's submitted
and passed counts and average. Students with nothing to follow up are only counted, in
`passed_all_count`. Every assessment counts for every class, because there is no record
of which assessments a class was given. Returns 404 if the class does not exist.
````

If the user's README edit from 2026-10-11 (the stale-test note now pointing to
`../NOTES.md`) is still uncommitted, it is in a different place and must survive.

**Verify:** `git -C .. diff python/README.md` shows the new section. Apart from that
user edit, if it is still uncommitted, it shows nothing else.

---

## Phase 10: Final check and report

1. Run the tests. Expected: `1 failed, 44 passed`, and the only failure is
   `test_submit_returns_500_before_scoring_implemented`.
2. `git -C .. status --short python`. Expected exactly these seven entries:
   ```text
    M python/README.md
    M python/src/app.py
    M python/src/database.py
    M python/src/models.py
   ?? python/src/class_summary.py
   ?? python/tests/test_class_summary.py
   ?? python/tests/test_class_summary_api.py
   ```
3. Report to the user, without committing:
   - The test summary line and both flake8 results.
   - The smoke-test result, or that it was skipped (8.2).
   - The files changed, grouped by phase, so each phase can be reviewed and committed
     on its own.
   - Any entries outside `python/` that Phase 0 noted.
   - **Deliberately untested** (lean suite, S12 and S20):
     - ties in the `failed` order;
     - a failed submission with no failed section (possible only when section weights
       don't sum to 1);
     - a stored submission missing a section;
     - an empty roster;
     - an assessment with no sections in `get_all_assessment_details`.
   - Any standards concern noticed, listed as a possible follow-up rather than changed
     (rule 12).
   - A reminder that `../NOTES.md` is the user's own writing to update.

---

## Appendix A: expected summaries from the seed data

| Class | `failed` (in order) | `not_submitted` (in order) | `sections_to_reteach` | `passed_all_count` |
|---|---|---|---|---|
| 12A `class-001` | Priya 0.7 (Comprehension), Alex 0.733 (Vocabulary) | Sam [Reading, Math], Jordan [Math], Priya [Math], Alex [Math] | none | 1 (Maya) |
| 12B `class-002` | Riley 0.15 (both), Casey 0.717 (both), Alex 0.733 (Vocabulary) | Sam [Reading, Math], Morgan [Reading, Math], Alex [Math], Casey [Math], Riley [Math] | Reading Vocabulary (0 of 3), Reading Comprehension (1 of 3) | 0 |
| 12C `class-003` | Riley 0.15 (both), Taylor 0.667 Math (both), Casey 0.717 (both), Jamie 0.85 (Comprehension) | Casey [Math], Riley [Math], Jamie [Math] | Reading Comprehension (1 of 4) | 0 |

Assessment rows:

| Class | Reading: submitted / passed / average | Math: submitted / passed / average |
|---|---|---|
| 12A | 4 / 2 / 0.858 | 1 / 1 / 1.0 |
| 12B | 3 / 0 / 0.533 | 0 / 0 / null |
| 12C | 4 / 1 / 0.679 | 1 / 0 / 0.667 |

## Appendix B: pitfalls (what goes wrong and how you would notice)

| Pitfall | Symptom |
|---|---|
| Running the tests without `--build` | Counts don't change after a phase; new tests "not found" |
| A **Find** block fails on CRLF | The Edit tool reports no match; stop (rule 5) |
| Forgetting `get_class_submissions` in the `app.py` imports | 500 errors on the new route; the API tests fail |
| Filtering students with `StudentResult.status` instead of the submission | Works, but `submission` stays typed `Optional`; see S10 |
| Sorting `failed` with `max` instead of `min` | Riley ranks by the 0.833 Math; unit `test_failed_lists_students_worst_first_...` fails |
| `<=` instead of `<` for the pass share in `needs_reteach` | Vocabulary at exactly half gets flagged; the unit and API `..._flags_sections_fewer_than_half_passed` tests fail |
| `>` instead of `>=` for the submitted guard | 2 of 4 submitted is no longer judged; `test_needs_reteach_judges_only_once_...` fails |
| Dropping the submitted guard | 12C Math is flagged from one submission; the guard test and the API reteach test fail |
| Building section stats from every submission instead of the roster's | Unit Vocabulary becomes 2 of 5 passed and is flagged; the reteach and overview unit tests fail |
| Writing `/tmp/check.db` checks against `data/` | The host's persistent database changes; always use `/tmp` inside the container |
