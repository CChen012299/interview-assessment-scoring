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
