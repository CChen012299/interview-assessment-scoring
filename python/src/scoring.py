import unicodedata

from src.config import MASTERY_THRESHOLD

# Float sums can land just under the true value: 80% everywhere with weights
# 0.1 / 0.7 / 0.2 sums to 0.7999999999999999.
_FLOAT_TOLERANCE = 1e-9


def _meets_threshold(percentage: float) -> bool:
    return percentage >= MASTERY_THRESHOLD - _FLOAT_TOLERANCE


def _normalize(answer: str) -> str:
    # NFC so "café" typed as one character or as e + combining accent compares equal.
    return unicodedata.normalize("NFC", answer).casefold()


def calculate_score(
    submitted_answers: dict[str, str],
    sections: list[dict],
) -> dict:
    """
    Score a student's submitted answers across a sectioned assessment.

    Each section has a weight and its own set of questions. The student must
    meet the mastery threshold both overall (weighted) and in each section
    individually to pass.

    Args:
        submitted_answers: maps question_id -> student's answer string
        sections: list of section dicts, each with:
            - id        (str):            section identifier
            - name      (str):            display name
            - weight    (float):          contribution to overall score (all weights sum to 1.0)
            - questions (dict[str, str]): maps question_id -> correct answer string

    Returns a dict with:
        section_scores     (list): one entry per section, each with:
            - id               (str)
            - name             (str)
            - points_earned    (int)
            - points_possible  (int)
            - percentage       (float): 0.0 to 1.0
            - passed           (bool):  True if percentage >= MASTERY_THRESHOLD
        overall_percentage  (float): weighted average across all sections
        passed              (bool):  True only if overall_percentage >= MASTERY_THRESHOLD
                                     AND every individual section passed

    Rules:
        - Questions not answered by the student count as incorrect
        - Answers submitted for questions not in any section are ignored
        - Comparison is case-insensitive
        - An empty submission is valid and scores 0 in all sections
        - Section weights are guaranteed to sum to 1.0

    Raises:
        ValueError: if a section has no questions (a broken assessment).
    """
    normalized_answers = {
        question_id: _normalize(answer)
        for question_id, answer in submitted_answers.items()
    }

    section_scores = []
    overall_percentage = 0.0

    for section in sections:
        questions = section["questions"]
        points_possible = len(questions)
        if points_possible == 0:
            raise ValueError(f"Section {section['id']!r} has no questions")

        # Walk the section's questions, not the answers: unanswered ones score 0
        # and answers to other questions are ignored.
        points_earned = sum(
            1
            for question_id, correct_answer in questions.items()
            if normalized_answers.get(question_id) == _normalize(correct_answer)
        )
        percentage = points_earned / points_possible

        section_scores.append(
            {
                "id": section["id"],
                "name": section["name"],
                "points_earned": points_earned,
                "points_possible": points_possible,
                "percentage": percentage,
                "passed": _meets_threshold(percentage),
            }
        )
        overall_percentage += percentage * section["weight"]

    passed = _meets_threshold(overall_percentage) and all(
        score["passed"] for score in section_scores
    )

    return {
        "section_scores": section_scores,
        "overall_percentage": overall_percentage,
        "passed": passed,
    }
