from typing import Literal

from pydantic import BaseModel


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


StudentResultStatus = Literal["passed", "not_passed", "not_submitted"]


class StudentAssessmentResult(BaseModel):
    student_id: str
    student_name: str
    status: StudentResultStatus
    overall_percentage: float | None = None
    section_scores: list[SectionScoreResponse] = []


class SectionResultSummary(BaseModel):
    id: str
    name: str
    average_percentage: float | None
    not_passed_student_ids: list[str]


class ClassResultsSummary(BaseModel):
    passed: int
    not_passed: int
    not_submitted: int
    average_overall_percentage: float | None
    sections: list[SectionResultSummary]


class ClassAssessmentResultsResponse(BaseModel):
    class_id: str
    class_name: str
    teacher_name: str
    assessment_id: str
    assessment_name: str
    summary: ClassResultsSummary
    students: list[StudentAssessmentResult]
