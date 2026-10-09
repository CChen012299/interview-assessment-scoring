from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, computed_field


class SubmitRequest(BaseModel):
    student_id: str
    answers: dict[str, str] = {}


class SectionScoreResponse(BaseModel):
    id: str
    name: str
    points_earned: int
    points_possible: int
    percentage: float
    passed: bool


class SubmissionResponse(BaseModel):
    submission_id: str
    student_id: str
    assessment_id: str
    section_scores: list[SectionScoreResponse]
    overall_percentage: float
    passed: bool


class SubmissionResponseList(BaseModel):
    responses: list[SubmissionResponse]


class StudentSummary(BaseModel):
    id: str
    name: str


class ClassResponse(BaseModel):
    id: str
    name: str
    teacher_name: str
    students: list[StudentSummary]


class ClassSummary(BaseModel):
    id: str
    name: str


class ClassList(BaseModel):
    classes: list[ClassSummary]


class AssessmentSummary(BaseModel):
    id: str
    name: str


class AssessmentList(BaseModel):
    assessments: list[AssessmentSummary]


class SectionSummary(BaseModel):
    id: str
    name: str
    weight: float


class AssessmentDetailResponse(BaseModel):
    id: str
    name: str
    sections: list[SectionSummary]


class QuestionAnswer(BaseModel):
    id: str
    correct_answer: str


class ScoringSection(BaseModel):
    id: str
    name: str
    weight: float
    questions: list[QuestionAnswer]


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
