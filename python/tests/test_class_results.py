import pytest

ALL_CORRECT_ASSESS_001 = {
    "q-001": "author", "q-002": "setting", "q-003": "plot",
    "q-004": "main idea", "q-005": "inference", "q-006": "evidence", "q-007": "summary",
}


def _results(client, class_id="class-001", assessment_id="assess-001"):
    response = client.get(f"/classes/{class_id}/assessments/{assessment_id}/results")
    assert response.status_code == 200
    return response.json()


def _student(data, student_id):
    return next(s for s in data["students"] if s["student_id"] == student_id)


def test_every_rostered_student_has_a_status(test_client):
    data = _results(test_client)

    assert data["teacher_name"] == "Ms. Rivera"
    assert data["assessment_name"] == "Grade 3 Reading"
    assert {s["student_id"]: s["status"] for s in data["students"]} == {
        "student-001": "passed",
        "student-002": "passed",
        "student-003": "not_passed",
        "student-004": "not_passed",
        "student-005": "not_submitted",
    }


def test_students_include_section_detail(test_client):
    data = _results(test_client)

    priya = _student(data, "student-003")
    assert priya["overall_percentage"] == pytest.approx(0.7)
    comprehension = next(s for s in priya["section_scores"] if s["id"] == "sec-002")
    assert comprehension["points_earned"] == 2
    assert comprehension["passed"] is False

    sam = _student(data, "student-005")
    assert sam["overall_percentage"] is None
    assert sam["section_scores"] == []


def test_summary_counts_statuses_and_shows_who_struggled_per_section(test_client):
    summary = _results(test_client)["summary"]

    assert (summary["passed"], summary["not_passed"], summary["not_submitted"]) == (2, 2, 1)

    sections = {s["id"]: s for s in summary["sections"]}
    assert sections["sec-001"]["average_percentage"] == pytest.approx(0.833, abs=0.001)
    assert sections["sec-001"]["not_passed_student_ids"] == ["student-004"]
    assert sections["sec-002"]["average_percentage"] == pytest.approx(0.875)
    assert sections["sec-002"]["not_passed_student_ids"] == ["student-003"]


def test_only_rostered_students_are_included(test_client):
    # Students from other classes also took assess-001.
    data = _results(test_client, class_id="class-002")

    ids = {s["student_id"] for s in data["students"]}
    assert ids == {"student-004", "student-005", "student-006", "student-007", "student-008"}
    assert data["summary"]["not_submitted"] == 2


def test_class_with_no_submissions_has_null_averages(test_client):
    summary = _results(test_client, class_id="class-002", assessment_id="assess-002")["summary"]

    assert summary["not_submitted"] == 5
    assert summary["average_overall_percentage"] is None
    assert all(s["average_percentage"] is None for s in summary["sections"])


def test_latest_submission_replaces_previous_result(test_client):
    test_client.post(
        "/assessments/assess-001/submit",
        json={"student_id": "student-003", "answers": ALL_CORRECT_ASSESS_001},
    )
    data = _results(test_client)

    assert [s["status"] for s in data["students"] if s["student_id"] == "student-003"] == ["passed"]
    assert data["summary"]["passed"] == 3


def test_404_for_unknown_class_or_assessment(test_client):
    response = test_client.get("/classes/does-not-exist/assessments/assess-001/results")
    assert response.status_code == 404
    assert response.json()["detail"] == "Class not found"

    response = test_client.get("/classes/class-001/assessments/does-not-exist/results")
    assert response.status_code == 404
    assert response.json()["detail"] == "Assessment not found"
