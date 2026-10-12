import pytest


def test_get_class_summary_returns_404_for_unknown_class(test_client):
    response = test_client.get("/classes/does-not-exist/summary")
    assert response.status_code == 404
    assert response.json()["detail"] == "Class not found"


def test_get_class_summary_lists_failed_students_worst_first(test_client):
    # Room 12B. Nobody in it has taken Grade 3 Math, so nobody has failed it
    response = test_client.get("/classes/class-002/summary")
    assert response.status_code == 200
    failed = response.json()["failed"]
    assert [s["id"] for s in failed] == [
        "student-007",  # Riley Johnson, 15%
        "student-006",  # Casey Kim, 71.7%
        "student-004",  # Alex Thompson, 73.3%
    ]
    alex = failed[2]
    assert [a["id"] for a in alex["assessments"]] == ["assess-001"]
    # Alex passed Comprehension, so only Vocabulary (1/3) is listed
    failed_sections = alex["assessments"][0]["failed_sections"]
    assert [s["name"] for s in failed_sections] == ["Vocabulary"]
    assert failed_sections[0]["points_earned"] == 1


def test_get_class_summary_lists_not_submitted_for_every_assessment(test_client):
    # Room 12A. Every assessment counts for every class, so Grade 3 Math, which
    # only Maya has taken, is listed for everyone else
    response = test_client.get("/classes/class-001/summary")
    assert response.status_code == 200
    not_submitted = response.json()["not_submitted"]
    assert [(s["id"], [a["id"] for a in s["assessments"]]) for s in not_submitted] == [
        ("student-005", ["assess-001", "assess-002"]),  # Sam Rivera
        ("student-002", ["assess-002"]),                # Jordan Williams
        ("student-003", ["assess-002"]),                # Priya Patel
        ("student-004", ["assess-002"]),                # Alex Thompson
    ]
    # Maya passed both assessments, so Maya is counted, not listed
    assert response.json()["passed_all_count"] == 1


def test_get_class_summary_flags_sections_fewer_than_half_passed(test_client):
    # Room 12C, 4 students:
    #   Reading Comprehension: 1 of 4 passed -> flagged
    #   Reading Vocabulary: 2 of 4 passed, exactly half -> not flagged
    #   Math: only Taylor has submitted (1 of 4, under half the roster), so it
    #   is not judged, even though 0 of 1 passed
    response = test_client.get("/classes/class-003/summary")
    assert response.status_code == 200
    flagged = response.json()["sections_to_reteach"]
    assert [(r["assessment"]["id"], r["section"]["name"]) for r in flagged] == [
        ("assess-001", "Comprehension")
    ]
    # (0.75 + 0.25 + 1.0 + 0.75) / 4 = 0.6875
    section = flagged[0]["section"]
    assert section["submitted_count"] == 4
    assert section["passed_count"] == 1
    assert section["average_percentage"] == pytest.approx(0.6875)


def test_get_class_summary_gives_headline_numbers_per_assessment(test_client):
    # Room 12B: 3 of 5 took Reading and none passed; nobody has taken Math
    response = test_client.get("/classes/class-002/summary")
    assert response.status_code == 200
    reading, math = response.json()["assessments"]
    assert reading["id"] == "assess-001"
    assert reading["submitted_count"] == 3
    assert reading["passed_count"] == 0
    # (0.733 + 0.717 + 0.15) / 3 = 0.533
    assert reading["average_overall_percentage"] == pytest.approx(0.533, abs=0.001)
    assert math["id"] == "assess-002"
    assert math["submitted_count"] == 0
    assert math["average_overall_percentage"] is None


def test_get_class_summary_reflects_a_new_submission(test_client):
    # End to end: Sam answers only the Vocabulary questions, so the submission
    # scores 0.4*1.0 + 0.6*0.0 = 0.4 and fails Comprehension
    submit = test_client.post(
        "/assessments/assess-001/submit",
        json={
            "student_id": "student-005",
            "answers": {"q-001": "author", "q-002": "setting", "q-003": "plot"},
        },
    )
    assert submit.status_code == 200
    response = test_client.get("/classes/class-001/summary")
    assert response.status_code == 200
    data = response.json()
    # Sam (0.4) is now furthest from passing, ahead of Priya (0.7) and Alex (0.733)
    assert [s["id"] for s in data["failed"]] == [
        "student-005", "student-003", "student-004"
    ]
    sam_reading = data["failed"][0]["assessments"][0]
    assert sam_reading["overall_percentage"] == pytest.approx(0.4)
    assert [s["name"] for s in sam_reading["failed_sections"]] == ["Comprehension"]
    sam = next(s for s in data["not_submitted"] if s["id"] == "student-005")
    assert [a["id"] for a in sam["assessments"]] == ["assess-002"]
