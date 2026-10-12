from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException

from src.class_results import build_student_results, summarize_class_results
from src.class_summary import summarize_class
from src.database import (
    get_all_assessment_details,
    get_assessment_detail,
    get_assessment_with_sections,
    get_assessments,
    get_class_submissions,
    get_class_submissions_for_assessment,
    get_class_with_students,
    get_classes,
    get_submissions_for_student,
    init_db,
    save_submission,
)
from src.models import (
    AssessmentDetailResponse,
    AssessmentSummary,
    ClassAssessmentResultsResponse,
    ClassResponse,
    ClassSummary,
    ClassSummaryResponse,
    SectionScoreResponse,
    SubmissionResponse,
    SubmitRequest,
)
from src.scoring import calculate_score

_DB_PATH = Path(__file__).parent.parent / "data" / "assessments.db"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(_DB_PATH)
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/assessments/{assessment_id}/submit")
def submit(assessment_id: str, body: SubmitRequest) -> SubmissionResponse:
    assessment = get_assessment_with_sections(assessment_id, _DB_PATH)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")

    sections = [
        {
            "id": section.id,
            "name": section.name,
            "weight": section.weight,
            "questions": {q.id: q.correct_answer for q in section.questions},
        }
        for section in assessment.sections
    ]
    result = calculate_score(body.answers, sections)

    section_scores = [
        SectionScoreResponse.model_validate(score)
        for score in result["section_scores"]
    ]

    submission_id = save_submission(
        student_id=body.student_id,
        assessment_id=assessment_id,
        section_scores=section_scores,
        overall_percentage=result["overall_percentage"],
        passed=result["passed"],
        db_path=_DB_PATH,
    )
    return SubmissionResponse(
        submission_id=submission_id,
        student_id=body.student_id,
        assessment_id=assessment_id,
        section_scores=section_scores,
        overall_percentage=result["overall_percentage"],
        passed=result["passed"],
    )


@app.get("/students/{student_id}/scores")
def get_scores(student_id: str) -> list[SubmissionResponse]:
    return get_submissions_for_student(student_id, _DB_PATH).responses


@app.get("/classes")
def list_classes() -> list[ClassSummary]:
    return get_classes(_DB_PATH).classes


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


@app.get("/assessments")
def list_assessments() -> list[AssessmentSummary]:
    return get_assessments(_DB_PATH).assessments


@app.get("/assessments/{assessment_id}")
def get_assessment(assessment_id: str) -> AssessmentDetailResponse:
    result = get_assessment_detail(assessment_id, _DB_PATH)
    if result is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return result
