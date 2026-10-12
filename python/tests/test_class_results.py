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
