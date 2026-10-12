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
