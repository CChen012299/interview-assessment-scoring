"""Builds the class results view from a roster, an assessment and its submissions."""

from collections import Counter

from src.models import (
    AssessmentDetailResponse,
    ClassAssessmentResultsResponse,
    ClassResponse,
    ClassResultsSummary,
    SectionResultSummary,
    StudentAssessmentResult,
    StudentSummary,
    SubmissionResponse,
)


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _student_result(
    student: StudentSummary, submission: SubmissionResponse | None
) -> StudentAssessmentResult:
    if submission is None:
        return StudentAssessmentResult(
            student_id=student.id, student_name=student.name, status="not_submitted"
        )
    # Use the stored result so this view matches what the student was told.
    return StudentAssessmentResult(
        student_id=student.id,
        student_name=student.name,
        status="passed" if submission.passed else "not_passed",
        overall_percentage=submission.overall_percentage,
        section_scores=submission.section_scores,
    )


def build_class_assessment_results(
    klass: ClassResponse,
    assessment: AssessmentDetailResponse,
    submissions_by_student: dict[str, SubmissionResponse],
) -> ClassAssessmentResultsResponse:
    students = [
        _student_result(student, submissions_by_student.get(student.id))
        for student in klass.students
    ]
    submitted = [s for s in students if s.status != "not_submitted"]

    sections = []
    for section in assessment.sections:
        scores = [
            (student.student_id, score)
            for student in submitted
            for score in student.section_scores
            if score.id == section.id
        ]
        sections.append(
            SectionResultSummary(
                id=section.id,
                name=section.name,
                average_percentage=_mean([score.percentage for _, score in scores]),
                not_passed_student_ids=[
                    student_id for student_id, score in scores if not score.passed
                ],
            )
        )

    counts = Counter(s.status for s in students)
    summary = ClassResultsSummary(
        passed=counts["passed"],
        not_passed=counts["not_passed"],
        not_submitted=counts["not_submitted"],
        average_overall_percentage=_mean([s.overall_percentage for s in submitted]),
        sections=sections,
    )

    return ClassAssessmentResultsResponse(
        class_id=klass.id,
        class_name=klass.name,
        teacher_name=klass.teacher_name,
        assessment_id=assessment.id,
        assessment_name=assessment.name,
        summary=summary,
        students=students,
    )
