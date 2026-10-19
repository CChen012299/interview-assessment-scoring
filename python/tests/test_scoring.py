import pytest
from src.scoring import calculate_score
from src.config import MASTERY_THRESHOLD

SECTIONS = [
    {
        "id": "sec-vocab",
        "name": "Vocabulary",
        "weight": 0.4,
        "questions": {"q1": "author", "q2": "setting", "q3": "plot"}
    },
    {
        "id": "sec-comp",
        "name": "Comprehension",
        "weight": 0.6,
        "questions": {"q4": "main idea", "q5": "inference", "q6": "evidence"}
    }
]


def test_all_sections_pass_returns_passed():
    answers = {"q1": "author", "q2": "setting", "q3": "plot",
               "q4": "main idea", "q5": "inference", "q6": "evidence"}
    result = calculate_score(answers, SECTIONS)
    assert result["passed"] is True
    assert result["overall_percentage"] == pytest.approx(1.0)
    assert all(s["passed"] for s in result["section_scores"])


def test_failed_section_fails_overall_even_if_weighted_average_passes():
    # vocab: 0/3 = 0% (fails); comp: 3/3 = 100% (passes)
    # weighted avg: 0*0.4 + 1.0*0.6 = 0.6 — below threshold
    answers = {"q4": "main idea", "q5": "inference", "q6": "evidence"}
    result = calculate_score(answers, SECTIONS)
    assert result["passed"] is False
    vocab = next(s for s in result["section_scores"] if s["id"] == "sec-vocab")
    assert vocab["passed"] is False


def test_weighted_average_below_threshold_fails_overall():
    # vocab: 3/3 (100%), comp: 2/3 (66.7% — fails threshold)
    answers = {"q1": "author", "q2": "setting", "q3": "plot",
               "q4": "main idea", "q5": "inference"}
    result = calculate_score(answers, SECTIONS)
    comp = next(s for s in result["section_scores"] if s["id"] == "sec-comp")
    assert comp["passed"] is False
    assert result["passed"] is False


def test_weights_applied_correctly_to_overall_percentage():
    # vocab: 2/3, comp: 3/3
    # weighted: (2/3)*0.4 + (3/3)*0.6 = 0.267 + 0.6 = 0.867
    answers = {"q1": "author", "q2": "setting",
               "q4": "main idea", "q5": "inference", "q6": "evidence"}
    result = calculate_score(answers, SECTIONS)
    assert result["overall_percentage"] == pytest.approx(0.867, abs=0.001)


def test_unanswered_questions_score_zero_in_their_section():
    answers = {"q4": "main idea", "q5": "inference", "q6": "evidence"}
    result = calculate_score(answers, SECTIONS)
    vocab = next(s for s in result["section_scores"] if s["id"] == "sec-vocab")
    assert vocab["points_earned"] == 0
    assert vocab["points_possible"] == 3


def test_empty_submission_scores_zero_everywhere():
    result = calculate_score({}, SECTIONS)
    assert result["overall_percentage"] == pytest.approx(0.0)
    assert result["passed"] is False
    for section in result["section_scores"]:
        assert section["points_earned"] == 0
        assert section["percentage"] == pytest.approx(0.0)


def test_comparison_is_case_insensitive():
    answers = {"q1": "AUTHOR", "q2": "Setting", "q3": "pLoT",
               "q4": "Main Idea", "q5": "INFERENCE", "q6": "evidence"}
    assert calculate_score(answers, SECTIONS)["passed"] is True

    # Same visible text typed two ways: "é" as one character vs "e" + accent.
    sections = [{"id": "s", "name": "S", "weight": 1.0,
                 "questions": {"q1": "caf\u00e9", "q2": "stra\u00dfe"}}]
    result = calculate_score({"q1": "CAFE\u0301", "q2": "STRASSE"}, sections)
    assert result["section_scores"][0]["points_earned"] == 2


def test_answers_for_unknown_questions_are_ignored():
    answers = {"q1": "author", "q2": "setting", "q3": "plot",
               "q4": "main idea", "q5": "inference", "q6": "evidence",
               "q-not-on-test": "anything", "q99": "author"}
    result = calculate_score(answers, SECTIONS)
    assert result["passed"] is True
    for section in result["section_scores"]:
        assert section["points_earned"] == section["points_possible"]


def test_exactly_at_threshold_passes_despite_float_rounding():
    # 4/5 = 80% in every section. With these weights a naive weighted sum is
    # 0.7999999999999999, which would wrongly fail a student who hit mastery.
    def section(sec_id, weight):
        questions = {f"{sec_id}-q{i}": "x" for i in range(5)}
        return {"id": sec_id, "name": sec_id, "weight": weight, "questions": questions}

    sections = [section("a", 0.1), section("b", 0.7), section("c", 0.2)]
    answers = {f"{s['id']}-q{i}": "x" for s in sections for i in range(4)}

    result = calculate_score(answers, sections)
    assert result["overall_percentage"] == pytest.approx(MASTERY_THRESHOLD)
    assert all(s["passed"] for s in result["section_scores"])
    assert result["passed"] is True


def test_section_with_no_questions_raises():
    sections = [{"id": "empty", "name": "Empty", "weight": 1.0, "questions": {}}]
    with pytest.raises(ValueError):
        calculate_score({}, sections)
