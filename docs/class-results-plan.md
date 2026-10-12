# Implementation plan: class assessment results

**Feature:** `GET /classes/{class_id}/assessments/{assessment_id}/results` shows a teacher every
student's result on one assessment (passed, failed or not submitted, with section
breakdowns), plus a class-wide summary.

**Where:** repo `interview-assessment-scoring`, branch `akash`, Python service in `python/`.
Absolute path: `C:/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python`
(in Git Bash: `/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python`).

**Why it is built this way:** see `class-results-decisions.md`. Decision IDs such as **D4**
are referenced below; you do not need to read that file to execute this plan.

**Verified (2026-10-09):**
- Every code block below was applied to a scratch copy of this repo. Result: 31 passed,
  1 known failure, flake8 clean on all new code.
- Dependency versions resolved at verification time (`requirements.txt` is unpinned):
  fastapi 0.143.0, pydantic 2.14.0, starlette 1.7.0, pytest 9.1.1. If a Verify step
  fails in a way that looks unrelated to your edits, version drift is a possible cause;
  report it rather than working around it.

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
   file before editing it** (Edit tools require that). Each **Find** block appears exactly
   once in its file. Do not use `sed`, regular expressions or scripts to edit.
5. **Line endings.** Every existing file under `python/` except `src/scoring.py` has
   Windows (CRLF) line endings in the working tree, because git's `core.autocrlf` is
   `true`. The **Find** blocks below are shown with plain line breaks. An Edit tool
   matches them and keeps each file's existing endings. New files may end up with LF or
   CRLF endings depending on the tool; either is fine, because git normalizes endings on
   commit. Do not convert any file's line endings. If a **Find** block is reported as
   not found, stop and report it; do not strip line endings by hand.
6. **Never edit or delete** these files: `tests/conftest.py`, `tests/test_api.py`,
   `tests/test_scoring.py`, `src/scoring.py`, `src/config.py`, `data/seed.sql`,
   `requirements.txt`, `Dockerfile`, `docker-compose.yml`, anything in `../csharp/`,
   `../NOTES.md.template`, and the repo-root `../README.md` (Phase 9 edits the *other*
   README, `python/README.md`).
   **Creating** the two new test files in `python/tests/` (Phases 4 and 7) was explicitly
   requested by the user. Any memory or instruction that says "never modify
   python/tests/" refers to the three provided test files above. Put the new tests in
   `python/tests/`, never in a scratchpad.
7. **Never commit or push.** Leave every change in the working tree.
8. Run the tests with:
   ```bash
   cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && docker compose run --rm --build test 2>&1 | tail -15
   ```
   - `--build` is required. The Dockerfile copies `src/` and `tests/` into the image when
     it is built, and an older image already exists on this machine, so without `--build`
     you would be testing stale code.
   - `| tail -15` hides the image-build and per-test output. The last lines contain the
     failure summary and the final summary line, which is what the Verify steps check.
     Below, "run the tests" means this command.
   - **The exit code is always non-zero** because of the known failing test (next rule),
     so judge every run by its printed output, never by its exit code.
9. **Expected in every test run, in every phase:**
   - Exactly one failing test: `tests/test_api.py::test_submit_returns_500_before_scoring_implemented`.
     It asserts behavior from before scoring was implemented, and the user chose to leave
     it as is (**D23**). Do not fix, skip or delete it.
   - A `StarletteDeprecationWarning` about `httpx`. It predates this work. Ignore it.
10. If a **Verify** result differs from what the phase says, **stop**. Report the phase,
    the command and its full output. Do not improvise a fix.
11. Keep every line at 92 characters or fewer.
12. **The user's coding standards (CLAUDE.md) were already applied when this plan was
    written, with three deliberate exceptions.** Do not "fix" them:
    - Existing code gets no new docstrings, module docstrings or type hints (**D24**).
    - The new test files copy the style of the provided tests exactly: no module
      docstrings, and no docstrings or type hints on test functions or their small helper
      functions (**D19**).
    - The three over-long lines that already exist in `src/database.py` stay as they are
      (Phase 8).
    If you believe a standard is violated, list it under "Possible follow-ups" in your
    Phase 10 report instead of changing code.
13. Run commands in a Bash shell (Git Bash on Windows). The `python -c "..."` checks
    below rely on Bash quoting.

---

## Phase overview

| Phase | What | Files | Test result after the phase |
|---|---|---|---|
| 0 | Preflight: confirm the baseline | none | 1 failed, 15 passed |
| 1 | Refactor: extract `_row_to_submission` | `src/database.py` | 1 failed, 15 passed |
| 2 | Response models and computed `status` | `src/models.py` | 1 failed, 15 passed |
| 3 | Pure summarizer module | `src/class_results.py` (new) | 1 failed, 15 passed |
| 4 | Unit tests for the summarizer | `tests/test_class_results.py` (new) | 1 failed, 23 passed |
| 5 | Query: a class's submissions for an assessment | `src/database.py` | 1 failed, 23 passed |
| 6 | The route | `src/app.py` | 1 failed, 23 passed |
| 7 | API tests for the route | `tests/test_class_results_api.py` (new) | 1 failed, 31 passed |
| 8 | Lint and smoke test | none | unchanged |
| 9 | Document the endpoint | `README.md` (the one in `python/`) | unchanged |
| 10 | Final check and report | none | unchanged |

---

## Phase 0: Preflight

**Goal:** confirm the starting point before changing anything.

1. Run `git branch --show-current`. Expected: `akash`.
2. Run `git -C .. status --short`. The `-C ..` runs git from the repo root, so paths are
   shown from there. Expected: ` M NOTES.md.template` (the user's own edits; do not
   touch it), and possibly the plan files themselves. If any file under `python/` is
   listed, stop and report.
3. Run the tests (rule 8).

**Verify:** the final summary line contains `1 failed, 15 passed`, and the failing test is
`test_submit_returns_500_before_scoring_implemented`.

---

## Phase 1: Refactor: extract `_row_to_submission`

**Goal:** move the "database row to `SubmissionResponse`" conversion into one private helper
that Phase 5 can reuse (**D17**, DRY). Behavior must not change.

**Find** in `src/database.py`:
```python
    return SubmissionResponseList(
        responses=[
            SubmissionResponse(
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
            for row in rows
        ]
    )
```
**Replace with:**
```python
    return SubmissionResponseList(responses=[_row_to_submission(row) for row in rows])


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
```

`sqlite3` and `json` are already imported at the top of `src/database.py`. Do not add
imports.

**Verify (step 1 of 2).** The provided tests barely look inside a converted submission,
so check the conversion directly. This builds a throwaway database at `/tmp/t.db` inside
the container; always pass that path, because the default path points at `data/`, which
is mounted from the host.
```bash
cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && docker compose run --rm --build test python -c "from src.database import init_db, get_submissions_for_student as g; init_db('/tmp/t.db'); print([(s.submission_id, s.overall_percentage, s.passed, [(x.id, x.points_earned, x.points_possible) for x in s.section_scores]) for s in g('student-003', '/tmp/t.db').responses])"
```
Expected last line: `[('sub-003', 0.7, False, [('sec-001', 3, 3), ('sec-002', 2, 4)])]`

**Verify (step 2 of 2).** Run the tests: still `1 failed, 15 passed`.

---

## Phase 2: Response models and the computed `status`

**Goal:** add the response shapes. `status` is computed from `submission`, so it can never
disagree with it (**D4**, **D5**). Count fields end in `_count` (**D11**). Averages are
nullable because an average of nothing is undefined (**D9**).

**2.1** Imports at the top of the file.

**Find** in `src/models.py`:
```python
from pydantic import BaseModel
```
**Replace with:**
```python
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, computed_field
```

**2.2** Add the new models at the end of the file, after the last existing class.

**Find** in `src/models.py`:
```python
class AssessmentWithSections(BaseModel):
    id: str
    name: str
    sections: list[ScoringSection]
```
**Replace with:**
```python
class AssessmentWithSections(BaseModel):
    id: str
    name: str
    sections: list[ScoringSection]


class ResultStatus(StrEnum):
    """A student's outcome on one assessment, as shown in class results."""

    # StrEnum members are real strings: they serialize to JSON as "passed" etc.
    # and compare equal to those plain strings.
    PASSED = "passed"
    FAILED = "failed"
    NOT_SUBMITTED = "not_submitted"


class StudentResult(BaseModel):
    """One roster student's result on one assessment.

    Attributes:
        id: Student identifier.
        name: Student display name.
        submission: The student's stored submission for the assessment, or None
            if they have not submitted it.
    """

    id: str
    name: str
    submission: Optional[SubmissionResponse]

    @computed_field
    @property
    def status(self) -> ResultStatus:
        """The student's outcome on the assessment.

        ``passed`` or ``failed`` from the submission's stored verdict, or
        ``not_submitted`` when there is no submission.
        """
        # Derived from `submission` rather than stored, so the two can never
        # disagree. The stored verdict is read, not recomputed, so it reflects
        # the mastery rule in force when the student submitted.
        if self.submission is None:
            return ResultStatus.NOT_SUBMITTED
        if self.submission.passed:
            return ResultStatus.PASSED
        return ResultStatus.FAILED


class SectionResultSummary(BaseModel):
    """Class-wide performance on one section of an assessment.

    Counts and averages include only students who submitted.

    Attributes:
        id: Section identifier.
        name: Section display name.
        weight: Section's contribution to the overall score.
        submitted_count: Number of submissions that include this section.
        passed_count: How many of those met the mastery threshold.
        average_percentage: Mean section percentage (0.0 to 1.0) across those
            submissions, or None when nobody has submitted.
    """

    id: str
    name: str
    weight: float
    submitted_count: int
    passed_count: int
    average_percentage: Optional[float]


class ClassResultsSummary(BaseModel):
    """Headline numbers for one class on one assessment.

    Attributes:
        total_students: Students on the class roster.
        submitted_count: Roster students with a submission.
        passed_count: Students whose submission passed.
        failed_count: Students whose submission failed.
        not_submitted_count: Roster students without a submission.
        average_overall_percentage: Mean overall percentage across submitters,
            or None when nobody has submitted.
        sections: One summary per assessment section, in assessment order.
    """

    total_students: int
    submitted_count: int
    passed_count: int
    failed_count: int
    not_submitted_count: int
    average_overall_percentage: Optional[float]
    sections: list[SectionResultSummary]


class ClassAssessmentResultsResponse(BaseModel):
    """Response for ``GET /classes/{class_id}/assessments/{assessment_id}/results``.

    Attributes:
        class_id: Class identifier.
        class_name: Class display name.
        teacher_name: Name of the class's teacher.
        assessment_id: Assessment identifier.
        assessment_name: Assessment display name.
        summary: Class-wide counts and averages.
        students: Every roster student, ordered by student id.
    """

    class_id: str
    class_name: str
    teacher_name: str
    assessment_id: str
    assessment_name: str
    summary: ClassResultsSummary
    students: list[StudentResult]
```

**Verify (step 1 of 2).**
```bash
cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && docker compose run --rm --build test python -c "from src.models import StudentResult; print(StudentResult(id='s', name='n', submission=None).model_dump(mode='json'))"
```
Expected last line: `{'id': 's', 'name': 'n', 'submission': None, 'status': 'not_submitted'}`

**Verify (step 2 of 2).** Run the tests: still `1 failed, 15 passed`.

---

## Phase 3: The pure summarizer module

**Goal:** a new module that turns roster + submissions + section definitions into student
results and a class summary. It has no database or HTTP code (**D12**, Single
Responsibility). Averages exclude students who have not submitted (**D7**), and the section
list comes from the assessment definition (**D10**).

**Create** `src/class_results.py`:
```python
"""Class-level results for one assessment.

Pure functions that turn a class roster, the class's stored submissions and the
assessment's section definitions into per-student results and a class-wide
summary. Nothing here touches the database or HTTP, mirroring ``src.scoring``:
the route fetches the data, this module shapes it.

Pass/fail verdicts are read from the stored submissions, never recomputed, so
this module does not depend on ``MASTERY_THRESHOLD``.
"""

from collections import Counter
from statistics import fmean
from typing import Optional

from src.models import (
    ClassResultsSummary,
    ResultStatus,
    SectionResultSummary,
    SectionSummary,
    StudentResult,
    StudentSummary,
    SubmissionResponse,
)


def build_student_results(
    students: list[StudentSummary],
    submissions_by_student_id: dict[str, SubmissionResponse],
) -> list[StudentResult]:
    """Pair every roster student with their submission, if they have one.

    The roster drives the output, so students without a submission still appear
    (with ``submission=None``) and submissions from students who are not on the
    roster are ignored.

    Args:
        students: The class roster, in the order it should be returned.
        submissions_by_student_id: Stored submissions for the assessment, keyed
            by student id.

    Returns:
        One StudentResult per roster student, in roster order.
    """
    return [
        StudentResult(
            id=student.id,
            name=student.name,
            submission=submissions_by_student_id.get(student.id),
        )
        for student in students
    ]


def summarize_class_results(
    student_results: list[StudentResult],
    sections: list[SectionSummary],
) -> ClassResultsSummary:
    """Roll student results up into class-wide counts and averages.

    Averages include only students who submitted: a missing submission is "no
    data", not a score of zero, so it must not drag the class average down.

    Args:
        student_results: Every roster student's result, from
            :func:`build_student_results`.
        sections: The assessment's section definitions. Driving the section
            list from the definition (not from submissions) means every section
            is listed even when nobody has submitted.

    Returns:
        Status counts, the mean overall percentage and one summary per section,
        in the order ``sections`` was given.
    """
    status_counts = Counter(result.status for result in student_results)
    submissions = [
        result.submission for result in student_results if result.submission is not None
    ]

    return ClassResultsSummary(
        total_students=len(student_results),
        submitted_count=len(submissions),
        passed_count=status_counts[ResultStatus.PASSED],
        failed_count=status_counts[ResultStatus.FAILED],
        not_submitted_count=status_counts[ResultStatus.NOT_SUBMITTED],
        average_overall_percentage=_mean_or_none(
            [submission.overall_percentage for submission in submissions]
        ),
        sections=[_summarize_section(section, submissions) for section in sections],
    )


def _summarize_section(
    section: SectionSummary, submissions: list[SubmissionResponse]
) -> SectionResultSummary:
    """Summarize one section across the submissions that scored it.

    Section scores are matched by section id. A submission whose stored scores
    lack this section (for example, one saved before the section was added) is
    left out of this section's counts rather than counted as zero.

    Args:
        section: The section definition to summarize.
        submissions: Submissions from students on the roster.

    Returns:
        The section's submitted and passed counts and its mean percentage.
    """
    section_scores = [
        score
        for submission in submissions
        for score in submission.section_scores
        if score.id == section.id
    ]

    return SectionResultSummary(
        id=section.id,
        name=section.name,
        weight=section.weight,
        submitted_count=len(section_scores),
        passed_count=sum(1 for score in section_scores if score.passed),
        average_percentage=_mean_or_none([score.percentage for score in section_scores]),
    )


def _mean_or_none(values: list[float]) -> Optional[float]:
    """Return the mean of ``values``, or None when there are none to average.

    ``statistics.fmean`` raises ``StatisticsError`` on an empty list, and an
    average of nothing is undefined rather than zero, so None is returned.

    Args:
        values: Percentages between 0.0 and 1.0.

    Returns:
        The arithmetic mean, or None for an empty list.
    """
    if not values:
        return None
    return fmean(values)
```

**Verify (step 1 of 2).**
```bash
cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && docker compose run --rm --build test python -c "from src.class_results import build_student_results, summarize_class_results; print('ok')"
```
Expected last line: `ok`

**Verify (step 2 of 2).** Run the tests: still `1 failed, 15 passed`.

---

## Phase 4: Unit tests for the summarizer

**Goal:** 8 unit tests of `StudentResult.status`, `build_student_results` and
`summarize_class_results`, using hand-built models and no database. They copy the style
of `tests/test_scoring.py` (**D19**): plain functions, descriptive names, module-level
test data, comments that show the arithmetic, `pytest.approx` for floats, and no
docstrings or type hints. The status test for an 85% score that still failed is the one
that proves `status` reads the stored verdict instead of recomputing it (**D5**).

**Create** `tests/test_class_results.py`:
```python
import pytest
from src.class_results import build_student_results, summarize_class_results
from src.config import MASTERY_THRESHOLD
from src.models import (
    ResultStatus,
    SectionScoreResponse,
    SectionSummary,
    StudentResult,
    StudentSummary,
    SubmissionResponse,
)

SECTIONS = [
    SectionSummary(id="sec-vocab", name="Vocabulary", weight=0.4),
    SectionSummary(id="sec-comp", name="Comprehension", weight=0.6),
]


def _section_score(section_id, name, earned, possible):
    return SectionScoreResponse(
        id=section_id,
        name=name,
        points_earned=earned,
        points_possible=possible,
        percentage=earned / possible,
        passed=earned / possible >= MASTERY_THRESHOLD,
    )


def _submission(student_id, vocab, comp, overall, passed):
    # vocab and comp are (points_earned, points_possible)
    return SubmissionResponse(
        submission_id=f"sub-{student_id}",
        student_id=student_id,
        assessment_id="assess-test",
        section_scores=[
            _section_score("sec-vocab", "Vocabulary", *vocab),
            _section_score("sec-comp", "Comprehension", *comp),
        ],
        overall_percentage=overall,
        passed=passed,
    )


# Modeled on Room 12A in the seed data: one pass, two fails, one not submitted
ROSTER = [
    StudentSummary(id="student-001", name="Maya Chen"),
    StudentSummary(id="student-003", name="Priya Patel"),
    StudentSummary(id="student-004", name="Alex Thompson"),
    StudentSummary(id="student-005", name="Sam Rivera"),
]
SUBMISSIONS = {
    # vocab 3/3, comp 4/4 -> overall 1.0, passed
    "student-001": _submission(
        "student-001", vocab=(3, 3), comp=(4, 4), overall=1.0, passed=True
    ),
    # vocab 3/3, comp 2/4 -> overall 0.4*1.0 + 0.6*0.5 = 0.7, failed
    "student-003": _submission(
        "student-003", vocab=(3, 3), comp=(2, 4), overall=0.7, passed=False
    ),
    # vocab 1/3, comp 4/4 -> overall 0.4*0.333 + 0.6*1.0 = 0.733, failed
    "student-004": _submission(
        "student-004", vocab=(1, 3), comp=(4, 4), overall=0.733, passed=False
    ),
}


def test_status_is_passed_when_submission_passed():
    result = StudentResult(
        id="student-001", name="Maya Chen", submission=SUBMISSIONS["student-001"]
    )
    assert result.status == ResultStatus.PASSED


def test_status_uses_stored_verdict_even_when_overall_meets_threshold():
    # overall 0.4*1.0 + 0.6*0.75 = 0.85 clears the threshold, but Comprehension
    # (3/4 = 0.75) does not, so the stored verdict is a fail
    submission = _submission(
        "student-010", vocab=(3, 3), comp=(3, 4), overall=0.85, passed=False
    )
    result = StudentResult(id="student-010", name="Jamie Lee", submission=submission)
    assert result.status == ResultStatus.FAILED


def test_status_is_not_submitted_without_submission():
    result = StudentResult(id="student-005", name="Sam Rivera", submission=None)
    assert result.status == ResultStatus.NOT_SUBMITTED


def test_build_student_results_lists_every_roster_student_in_order():
    results = build_student_results(ROSTER, SUBMISSIONS)
    assert [r.id for r in results] == [
        "student-001", "student-003", "student-004", "student-005"
    ]
    assert results[1].submission == SUBMISSIONS["student-003"]
    assert results[3].submission is None


def test_build_student_results_ignores_submissions_from_students_not_on_roster():
    outsider = _submission(
        "student-999", vocab=(3, 3), comp=(4, 4), overall=1.0, passed=True
    )
    results = build_student_results(ROSTER, {**SUBMISSIONS, "student-999": outsider})
    assert "student-999" not in {r.id for r in results}


def test_summary_counts_students_by_status():
    summary = summarize_class_results(build_student_results(ROSTER, SUBMISSIONS), SECTIONS)
    assert summary.total_students == 4
    assert summary.submitted_count == 3
    assert summary.passed_count == 1
    assert summary.failed_count == 2
    assert summary.not_submitted_count == 1


def test_summary_averages_exclude_non_submitters():
    # overall: (1.0 + 0.7 + 0.733) / 3 submitters = 0.811 (Sam as 0 would give 0.608)
    # Vocabulary: (3/3 + 3/3 + 1/3) / 3 = 0.778, 2 of 3 passed
    # Comprehension: (4/4 + 2/4 + 4/4) / 3 = 0.833, 2 of 3 passed
    summary = summarize_class_results(build_student_results(ROSTER, SUBMISSIONS), SECTIONS)
    assert summary.average_overall_percentage == pytest.approx(0.811, abs=0.001)
    vocab = next(s for s in summary.sections if s.id == "sec-vocab")
    comp = next(s for s in summary.sections if s.id == "sec-comp")
    assert vocab.submitted_count == 3
    assert vocab.passed_count == 2
    assert vocab.average_percentage == pytest.approx(0.778, abs=0.001)
    assert comp.submitted_count == 3
    assert comp.passed_count == 2
    assert comp.average_percentage == pytest.approx(0.833, abs=0.001)


def test_summary_with_no_submissions_still_lists_every_section():
    summary = summarize_class_results(build_student_results(ROSTER, {}), SECTIONS)
    assert summary.submitted_count == 0
    assert summary.not_submitted_count == 4
    assert summary.average_overall_percentage is None
    assert [s.id for s in summary.sections] == ["sec-vocab", "sec-comp"]
    for section in summary.sections:
        assert section.submitted_count == 0
        assert section.average_percentage is None
```

**Verify:** run the tests. The summary line contains `1 failed, 23 passed` (8 new tests).

---

## Phase 5: Query: a class's submissions for an assessment

**Goal:** one query that fetches the stored submissions of students on a class roster for
one assessment. The roster itself comes from the existing `get_class_with_students`, so
this query only needs an inner JOIN (**D13**). `ORDER BY rowid` makes the result
deterministic, nothing more (**D16**).

Insert the new function between `get_submissions_for_student` and `_row_to_submission`.

**Find** in `src/database.py`:
```python
    return SubmissionResponseList(responses=[_row_to_submission(row) for row in rows])


def _row_to_submission(row: sqlite3.Row) -> SubmissionResponse:
```
**Replace with:**
```python
    return SubmissionResponseList(responses=[_row_to_submission(row) for row in rows])


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

    return {row["student_id"]: _row_to_submission(row) for row in rows}


def _row_to_submission(row: sqlite3.Row) -> SubmissionResponse:
```

**Verify (step 1 of 2).** A quick look at the query's result on the seed data. As in
Phase 1, always pass `/tmp/t.db`.
```bash
cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && docker compose run --rm --build test python -c "from src.database import init_db, get_class_submissions_for_assessment as f; init_db('/tmp/t.db'); print(sorted(f('class-001', 'assess-001', '/tmp/t.db')), sorted(f('class-003', 'assess-001', '/tmp/t.db')))"
```
Expected last line:
`['student-001', 'student-002', 'student-003', 'student-004'] ['student-006', 'student-007', 'student-009', 'student-010']`
In the first list, student-005 has not submitted. In the second, Maya (student-001)
submitted but is not on the class-003 roster.

**Verify (step 2 of 2).** Run the tests: still `1 failed, 23 passed`.

---

## Phase 6: The route

**Goal:** wire it together, following the existing `submit` route: the route fetches data
and handles 404s, and the pure module shapes the data (**D12**). The class is checked
before the assessment (**D14**).

**6.1** Import the summarizer (`src.class_results` sorts before `src.database`).

**Find** in `src/app.py`:
```python
from src.database import (
```
**Replace with:**
```python
from src.class_results import build_student_results, summarize_class_results
from src.database import (
```

**6.2** Import the new query (kept in alphabetical order).

**Find** in `src/app.py`:
```python
    get_assessments,
    get_class_with_students,
```
**Replace with:**
```python
    get_assessments,
    get_class_submissions_for_assessment,
    get_class_with_students,
```

**6.3** Import the response model.

**Find** in `src/app.py`:
```python
    AssessmentSummary,
    ClassResponse,
```
**Replace with:**
```python
    AssessmentSummary,
    ClassAssessmentResultsResponse,
    ClassResponse,
```

**6.4** Add the route directly after the existing `get_class` route.

**Find** in `src/app.py`:
```python
@app.get("/classes/{class_id}")
def get_class(class_id: str) -> ClassResponse:
    result = get_class_with_students(class_id, _DB_PATH)
    if result is None:
        raise HTTPException(status_code=404, detail="Class not found")
    return result
```
**Replace with:**
```python
@app.get("/classes/{class_id}")
def get_class(class_id: str) -> ClassResponse:
    result = get_class_with_students(class_id, _DB_PATH)
    if result is None:
        raise HTTPException(status_code=404, detail="Class not found")
    return result


# The \f (form feed) in the docstring ends the description FastAPI shows on
# /docs, so the Args/Returns/Raises sections below it stay out of the API docs.
@app.get("/classes/{class_id}/assessments/{assessment_id}/results")
def get_class_results(class_id: str, assessment_id: str) -> ClassAssessmentResultsResponse:
    """Return each roster student's result on one assessment, plus a class summary.

    Every student on the class roster is listed, including those who have not
    submitted (``status`` is ``"not_submitted"`` and ``submission`` is null).
    \f
    Args:
        class_id: Class whose roster to report on.
        assessment_id: Assessment to report results for.

    Returns:
        Class and assessment details, a class-wide summary and one result per
        roster student.

    Raises:
        HTTPException: 404 if the class does not exist, or if the assessment
            does not exist. The class is checked first.
    """
    class_ = get_class_with_students(class_id, _DB_PATH)
    if class_ is None:
        raise HTTPException(status_code=404, detail="Class not found")

    assessment = get_assessment_detail(assessment_id, _DB_PATH)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")

    submissions = get_class_submissions_for_assessment(class_id, assessment_id, _DB_PATH)
    student_results = build_student_results(class_.students, submissions)

    return ClassAssessmentResultsResponse(
        class_id=class_.id,
        class_name=class_.name,
        teacher_name=class_.teacher_name,
        assessment_id=assessment.id,
        assessment_name=assessment.name,
        summary=summarize_class_results(student_results, assessment.sections),
        students=student_results,
    )
```

Four details that look optional but are not:
- **`\f` is two characters: a backslash followed by the letter f.** Type exactly that,
  both in the comment and on its own line inside the docstring. Python turns the escape
  into a form-feed character when it reads the docstring, and FastAPI cuts the `/docs`
  description there (**D30**). Never put an actual form-feed byte in the file: it is
  invisible, and flake8 reports it as `W293` in Phase 8.
- **Every database call passes `_DB_PATH` explicitly.** The test fixture in
  `tests/conftest.py` swaps `src.app._DB_PATH` for a temporary file. A call that omits it
  would quietly read the real `data/assessments.db`.
- **The local variable is `class_`**, because `class` is a Python keyword. A trailing
  underscore is the convention PEP 8 recommends.
- **The route function is named `get_class_results`.** Do not give it the same name as an
  imported database function such as `get_class_submissions_for_assessment`, or the route
  would overwrite that import and call itself.

**Verify (step 1 of 2).** Run this exactly as shown. The Python lines inside the quotes
must start at the left margin, with no extra indentation:

```bash
cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && docker compose run --rm --build test python -c "
import pathlib, tempfile
import src.app as m
m._DB_PATH = pathlib.Path(tempfile.mkdtemp()) / 't.db'
from fastapi.testclient import TestClient
with TestClient(m.app) as c:
    r = c.get('/classes/class-001/assessments/assess-001/results')
    print(r.status_code, r.json()['summary']['passed_count'],
          [s['status'] for s in r.json()['students']])
    paths = c.get('/openapi.json').json()['paths']
    print('Args:' in str(paths['/classes/{class_id}/assessments/{assessment_id}/results']))
"
```

Expected last two lines:
```text
200 2 ['passed', 'passed', 'failed', 'failed', 'not_submitted']
False
```
`False` confirms the docstring's `Args:` section is not in the public API description. A
deprecation warning may print above these lines. Ignore it.

**Verify (step 2 of 2).** Run the tests: still `1 failed, 23 passed`.

---

## Phase 7: API tests for the route

**Goal:** 8 end-to-end tests through HTTP against the seeded database, copying the style
of `tests/test_api.py` (**D19**): the `test_client` fixture, literal URLs, the status
code asserted first. They cover:
- the two 404s
- every status, and the section breakdown
- summary counts, and averages that exclude non-submitters
- a real 0% score counting in averages (it is a score, not missing data)
- a class with no submissions still listing every section
- submit-then-read wiring end to end

**Create** `tests/test_class_results_api.py`:
```python
import pytest


def test_get_class_results_returns_404_for_unknown_class(test_client):
    response = test_client.get("/classes/does-not-exist/assessments/assess-001/results")
    assert response.status_code == 404
    assert response.json()["detail"] == "Class not found"


def test_get_class_results_returns_404_for_unknown_assessment(test_client):
    response = test_client.get("/classes/class-001/assessments/does-not-exist/results")
    assert response.status_code == 404
    assert response.json()["detail"] == "Assessment not found"


def test_get_class_results_returns_every_roster_student_with_status(test_client):
    response = test_client.get("/classes/class-001/assessments/assess-001/results")
    assert response.status_code == 200
    data = response.json()
    assert data["class_name"] == "Room 12A"
    assert data["assessment_name"] == "Grade 3 Reading"
    assert [(s["id"], s["status"]) for s in data["students"]] == [
        ("student-001", "passed"),         # Maya Chen, 100%
        ("student-002", "passed"),         # Jordan Williams, 100%
        ("student-003", "failed"),         # Priya Patel, Comprehension 2/4
        ("student-004", "failed"),         # Alex Thompson, Vocabulary 1/3
        ("student-005", "not_submitted"),  # Sam Rivera
    ]
    sam = next(s for s in data["students"] if s["id"] == "student-005")
    assert sam["submission"] is None


def test_get_class_results_includes_section_scores_for_submitters(test_client):
    response = test_client.get("/classes/class-001/assessments/assess-001/results")
    assert response.status_code == 200
    priya = next(s for s in response.json()["students"] if s["id"] == "student-003")
    assert priya["submission"]["overall_percentage"] == pytest.approx(0.7)
    comprehension = next(
        s for s in priya["submission"]["section_scores"] if s["name"] == "Comprehension"
    )
    assert comprehension["points_earned"] == 2
    assert comprehension["points_possible"] == 4
    assert comprehension["passed"] is False


def test_get_class_results_summary_excludes_non_submitters_from_averages(test_client):
    # Sam has not submitted, so averages are over the 4 submitters:
    # overall: (1.0 + 1.0 + 0.7 + 0.733) / 4 = 0.858
    # Vocabulary: (1.0 + 1.0 + 1.0 + 0.333) / 4 = 0.833, 3 of 4 passed
    response = test_client.get("/classes/class-001/assessments/assess-001/results")
    assert response.status_code == 200
    summary = response.json()["summary"]
    assert summary["total_students"] == 5
    assert summary["submitted_count"] == 4
    assert summary["passed_count"] == 2
    assert summary["failed_count"] == 2
    assert summary["not_submitted_count"] == 1
    assert summary["average_overall_percentage"] == pytest.approx(0.858, abs=0.001)
    vocab = next(s for s in summary["sections"] if s["name"] == "Vocabulary")
    assert vocab["passed_count"] == 3
    assert vocab["average_percentage"] == pytest.approx(0.833, abs=0.001)


def test_get_class_results_averages_count_a_zero_score_as_a_score(test_client):
    # Room 12B on Grade 3 Reading, Vocabulary: Alex 1/3, Casey 2/3, Riley 0/3
    # (0.333 + 0.667 + 0.0) / 3 = 0.333; dropping Riley's zero would give 0.5
    response = test_client.get("/classes/class-002/assessments/assess-001/results")
    assert response.status_code == 200
    sections = response.json()["summary"]["sections"]
    vocab = next(s for s in sections if s["name"] == "Vocabulary")
    assert vocab["submitted_count"] == 3
    assert vocab["average_percentage"] == pytest.approx(0.333, abs=0.001)


def test_get_class_results_with_no_submissions_lists_every_section(test_client):
    # Nobody in class-002 (Room 12B) has taken assess-002 (Grade 3 Math)
    response = test_client.get("/classes/class-002/assessments/assess-002/results")
    assert response.status_code == 200
    data = response.json()
    assert {s["status"] for s in data["students"]} == {"not_submitted"}
    assert data["summary"]["average_overall_percentage"] is None
    sections = data["summary"]["sections"]
    assert [s["name"] for s in sections] == ["Computation", "Word Problems"]
    assert all(s["average_percentage"] is None for s in sections)


def test_get_class_results_reflects_a_new_submission(test_client):
    # End to end: submit through the API, then read the class results back
    submit = test_client.post(
        "/assessments/assess-001/submit",
        json={
            "student_id": "student-005",
            "answers": {
                "q-001": "author",
                "q-002": "setting",
                "q-003": "plot",
                "q-004": "main idea",
                "q-005": "inference",
                "q-006": "evidence",
                "q-007": "summary",
            },
        },
    )
    assert submit.status_code == 200
    response = test_client.get("/classes/class-001/assessments/assess-001/results")
    assert response.status_code == 200
    data = response.json()
    sam = next(s for s in data["students"] if s["id"] == "student-005")
    assert sam["status"] == "passed"
    assert data["summary"]["passed_count"] == 3
    assert data["summary"]["not_submitted_count"] == 0
```

**Verify:** run the tests. The summary line contains `1 failed, 31 passed` (8 new tests).

---

## Phase 8: Lint and smoke test

**8.1 flake8 on the new and changed files.** flake8 is a PEP 8 style checker. It is not in
`requirements.txt`, so the command installs it inside the throwaway container. The pip
flags silence pip's "running as root" and "new version available" notices.
```bash
cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && docker compose run --rm --build test sh -c "pip install -q --root-user-action=ignore --disable-pip-version-check flake8 && flake8 --max-line-length 92 src/app.py src/class_results.py src/models.py tests/test_class_results.py tests/test_class_results_api.py && echo flake8-clean" 2>&1 | tail -5
```
Expected last line: `flake8-clean`.

Then check `src/database.py` separately:
```bash
cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && docker compose run --rm --build test sh -c "pip install -q --root-user-action=ignore --disable-pip-version-check flake8 && flake8 --max-line-length 92 src/database.py" 2>&1 | tail -5
```
Expected: exactly these three errors. Those lines predate this work and are not part of
this change, so leave them alone (rule 12). Any other error means a mistake in Phase 1
or 5.
```text
src/database.py:94:93: E501 line too long (95 > 92 characters)
src/database.py:104:93: E501 line too long (94 > 92 characters)
src/database.py:118:93: E501 line too long (94 > 92 characters)
```

**8.2 Smoke test against a running server.** Optional. Leave the user's environment the
way you found it.

First, check whether the API is already running:
```bash
cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && docker compose ps --status running api
```

**Case A:** a container named like `python-api-1` is listed. The user is running the API.
**Skip the rest of 8.2.** Do not restart, rebuild or stop it. In your Phase 10 report,
write: "Smoke test skipped: the API container was already running. Run
`docker compose up --build -d api` to load the new code."

**Case B:** only the header line is listed, so the API is not running. Start it, test it,
then stop and remove only the container you started:
```bash
cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && docker compose up --build -d api
curl -s --retry 10 --retry-all-errors --retry-delay 1 http://localhost:8000/classes/class-001/assessments/assess-001/results
curl -s --retry 10 --retry-all-errors --retry-delay 1 -o /dev/null -w "%{http_code}\n" http://localhost:8000/classes/nope/assessments/assess-001/results
cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && docker compose rm -sf api
```
- `docker compose up -d` returns as soon as the container starts, before the server is
  listening. The `--retry` flags make `curl` wait for it.
- If `docker compose up` reports that port 8000 is already allocated, skip this step and
  say so in your report.

Expected:
- The first `curl` prints JSON that starts with `{"class_id":"class-001","class_name":"Room 12A"`
  and contains `"summary"` and `"students"`.
- The second prints `404`.
- If either still prints nothing or `000` after the retries, run `docker compose logs api`
  and report its output.

Notes:
- In PowerShell, write `curl.exe`, because there `curl` is an alias for a different
  command.
- The numbers can differ from the tests if `data/assessments.db` holds extra submissions
  from earlier manual testing. The tests always use a fresh database.
- `http://localhost:8000/docs` shows the new endpoint and its schema.

---

## Phase 9: Document the endpoint

**Goal:** `python/README.md` is the API reference that reviewers read, so it gets the new
endpoint, plus a note about the one test that is expected to fail (**D29**).

Leave the rest of the README alone, including the provided exercise text ("What to
implement" and "All 16 should pass"). It is the brief, not documentation of this code.

**9.1 API reference.** The **Find** and **Replace with** text below is wrapped in
`~~~~markdown` and `~~~~` lines only so that the inner ```` ``` ```` fences display
correctly. Those `~~~~` lines are **not** part of the text; do not put them in
`README.md`.

**Find** in `README.md`:
~~~~markdown
### Get a class with its students

```bash
curl http://localhost:8000/classes/class-001
```
~~~~
**Replace with:**
~~~~markdown
### Get a class with its students

```bash
curl http://localhost:8000/classes/class-001
```

### Get a class's results for an assessment

```bash
curl http://localhost:8000/classes/class-001/assessments/assess-001/results
```

Lists every student on the class roster with a `status` of `passed`, `failed` or
`not_submitted`, and their `submission` (overall percentage and per-section scores), which
is `null` if they have not submitted. A `summary` gives status counts, the average overall
percentage, and, for each section of the assessment, how many students submitted, how many
passed and their average. Averages include only students who submitted and are `null` when
nobody has. Returns 404 if the class or the assessment does not exist.
~~~~

**9.2 Running the tests.**

**Find** in `README.md`:
```markdown
Before you implement the scoring function, 8 tests pass and 8 fail. All 16 should pass once your implementation is correct.
```
**Replace with:**
```markdown
Before you implement the scoring function, 8 tests pass and 8 fail. All 16 should pass once your implementation is correct.

One provided test, `test_submit_returns_500_before_scoring_implemented`, checks behavior
from before the scoring function existed and is expected to fail (see
`../NOTES.md.template`). After changing code, add `--build` so the image picks up your
changes: `docker compose run --rm --build test`.
```

**Verify:** count the code-fence lines; the number must be even (every fence closed):
```bash
cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && grep -c '^```' README.md
```
Expected: `18`. Then read both edited sections once to check they look right.

---

## Phase 10: Final check and report

This phase only checks and reports. It changes no files.

1. Run `git -C .. status --short`. Expected, and nothing else apart from the user's
   ` M NOTES.md.template` and an untracked line for wherever these plan files live (for
   example `?? plan/`):
   ```text
    M python/README.md
    M python/src/app.py
    M python/src/database.py
    M python/src/models.py
   ?? python/src/class_results.py
   ?? python/tests/test_class_results.py
   ?? python/tests/test_class_results_api.py
   ```
2. Confirm that the protected files are untouched:
   ```bash
   cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && git diff --quiet -- tests/conftest.py tests/test_api.py tests/test_scoring.py src/scoring.py src/config.py data/seed.sql requirements.txt Dockerfile docker-compose.yml && echo untouched
   ```
   Expected: `untouched`.
3. Run the tests one last time. Expected: `1 failed, 31 passed`.
4. Confirm that every new test passes. Every test named in Appendix A lives in these two
   files:
   ```bash
   cd "/c/Users/akash/OneDrive/Documents/GitHub/interview-assessment-scoring/python" && docker compose run --rm --build test pytest tests/test_class_results.py tests/test_class_results_api.py -q -p no:cacheprovider 2>&1 | tail -3
   ```
   Expected: a summary line containing `16 passed` and no failures.
5. Report what changed, phase by phase, including anything skipped (such as 8.2).
   **Do not commit.** The user will review and commit. End the report with "Possible
   follow-ups". Always include these known items, plus anything you noticed (rule 12):
   - Explain the stale `test_submit_returns_500_before_scoring_implemented` in
     `../NOTES.md.template` (D23); the README now points readers there.
   - Duplicate submission rows are possible in principle and would make the class view
     miss a resubmission (D16). The fix is a UNIQUE index on
     `submissions(student_id, assessment_id)` plus an upsert in `save_submission`.

---

## Appendix A: behavior checklist

Each behavior below has a test that asserts it.

| Behavior | Test(s) |
|---|---|
| Unknown class → 404 "Class not found" | `test_get_class_results_returns_404_for_unknown_class` |
| Unknown assessment → 404 "Assessment not found" | `test_get_class_results_returns_404_for_unknown_assessment` |
| Every roster student listed, in id order, with the right status; non-submitter has a null `submission` | `test_get_class_results_returns_every_roster_student_with_status`, `test_build_student_results_lists_every_roster_student_in_order`, `test_status_is_not_submitted_without_submission` |
| `status` comes from the stored verdict (85% overall can still fail) | `test_status_uses_stored_verdict_even_when_overall_meets_threshold`, `test_status_is_passed_when_submission_passed` |
| Section breakdown included for submitters | `test_get_class_results_includes_section_scores_for_submitters` |
| Summary counts by status | `test_summary_counts_students_by_status`, `test_get_class_results_summary_excludes_non_submitters_from_averages` |
| Averages exclude non-submitters | `test_summary_averages_exclude_non_submitters`, `test_get_class_results_summary_excludes_non_submitters_from_averages` |
| A real 0% score counts in averages | `test_get_class_results_averages_count_a_zero_score_as_a_score` |
| Sections come from the assessment definition, even with zero submissions | `test_summary_with_no_submissions_still_lists_every_section`, `test_get_class_results_with_no_submissions_lists_every_section` |
| Submissions from students not on the roster are ignored | `test_build_student_results_ignores_submissions_from_students_not_on_roster` |
| End to end: a new submission shows up | `test_get_class_results_reflects_a_new_submission` |

**Deliberately not covered by a test** (the user chose a lean test suite; see D19 and
D22): the class-before-assessment 404 order, the roster JOIN inside the query (the route
filters by roster anyway), matching stored section scores by id rather than name,
duplicate-row ordering, a student shown in two classes, an empty submission, and a
resubmission.

## Appendix B: pitfalls (what goes wrong and how you would notice)

| Pitfall | Symptom | Prevention |
|---|---|---|
| Ran tests without `--build` | Your changes "do nothing"; test counts don't move | Always `docker compose run --rm --build test` |
| Omitted `_DB_PATH` in a route call | Tests pass or fail depending on the real `data/assessments.db` | Pass `_DB_PATH` to every database call in `app.py` |
| Named the route after an imported function | `RecursionError` or a wrong response | Route name is `get_class_results` |
| Used `class` as a variable name | `SyntaxError` | Use `class_` |
| "Fixed" the stale 500 test | Diff touches `tests/test_api.py` | Never edit the provided test files (D23) |
| `python -c` check without `/tmp/t.db` | Writes to the host's `data/` folder | Always pass `'/tmp/t.db'` |
| Used `sed`, regex or a script for edits | Partial or duplicated edits; Find blocks "not found" because of CRLF | Edit tool only (rules 4 and 5) |
| Wrote a real form-feed byte instead of `\f` | flake8 `W293` on the docstring line in Phase 8.1 (the Phase 6 check still prints `False`, so it won't catch this) | Type backslash + `f` (Phase 6) |
| Judged a run by its exit code | Every run looks "failed" | The exit code is always non-zero; read the output (rule 8) |
| Treated pip's notices as errors | Phase 8 looks like it failed | The pip flags in 8.1 silence them |
| Restarted or stopped the user's running API | The user's server restarts or disappears | Phase 8.2 Case A: skip, do not touch it |
| Added docstrings or type hints to old code, or to the tests | Line numbers shift, so the flake8 lines in 8.1 no longer match; tests no longer match the existing style | Rule 12 |
