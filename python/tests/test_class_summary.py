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
