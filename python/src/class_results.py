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
