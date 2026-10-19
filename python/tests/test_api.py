import pytest


def test_submit_returns_422_on_missing_student_id(test_client):
    response = test_client.post(
        "/assessments/assess-001/submit",
        json={"answers": {"q-001": "author"}},
    )
    assert response.status_code == 422


def test_submit_returns_404_on_unknown_assessment(test_client):
    response = test_client.post(
        "/assessments/does-not-exist/submit",
        json={"student_id": "student-1", "answers": {}},
    )
    assert response.status_code == 404


def test_submit_scores_submission_end_to_end(test_client):
    # The README's example request.
    response = test_client.post(
        "/assessments/assess-001/submit",
        json={
            "student_id": "student-001",
            "answers": {"q-001": "author", "q-002": "setting", "q-004": "main idea"},
        },
    )
    assert response.status_code == 200
    data = response.json()
    sections = {s["id"]: s for s in data["section_scores"]}
    # Vocabulary 2/3, Comprehension 1/4 -> (2/3)*0.4 + (1/4)*0.6 = 0.4167
    assert sections["sec-001"]["points_earned"] == 2
    assert sections["sec-001"]["points_possible"] == 3
    assert sections["sec-002"]["points_earned"] == 1
    assert sections["sec-002"]["points_possible"] == 4
    assert data["overall_percentage"] == pytest.approx(0.4167, abs=0.001)
    assert data["passed"] is False


def test_get_scores_returns_empty_list_for_unknown_student(test_client):
    response = test_client.get("/students/brand-new-student/scores")
    assert response.status_code == 200
    assert response.json() == []


def test_get_classes_returns_list(test_client):
    response = test_client.get("/classes")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    ids = {c["id"] for c in data}
    assert ids == {"class-001", "class-002", "class-003"}


def test_get_class_returns_students_without_scores(test_client):
    response = test_client.get("/classes/class-001")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "class-001"
    assert data["name"] == "Room 12A"
    assert data["teacher_name"] == "Ms. Rivera"
    assert len(data["students"]) == 5
    assert "scores" not in data
    assert "submissions" not in data


def test_get_class_returns_404_for_unknown_class(test_client):
    response = test_client.get("/classes/does-not-exist")
    assert response.status_code == 404


def test_get_assessments_returns_list(test_client):
    response = test_client.get("/assessments")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    ids = {a["id"] for a in data}
    assert ids == {"assess-001", "assess-002"}


def test_submit_returns_score_result(test_client):
    response = test_client.post(
        "/assessments/assess-001/submit",
        json={
            "student_id": "student-abc",
            "answers": {
                "q-001": "author",
                "q-002": "setting",
                "q-003": "plot",
                "q-004": "main idea",
                "q-005": "inference",
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "submission_id" in data
    assert data["student_id"] == "student-abc"
    assert data["assessment_id"] == "assess-001"
    assert "overall_percentage" in data
    assert "passed" in data
    assert isinstance(data["section_scores"], list)
    assert len(data["section_scores"]) == 2


def test_get_scores_returns_submission_after_submit(test_client):
    test_client.post(
        "/assessments/assess-002/submit",
        json={"student_id": "student-xyz", "answers": {"q-008": "12"}},
    )
    response = test_client.get("/students/student-xyz/scores")
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["assessment_id"] == "assess-002"
