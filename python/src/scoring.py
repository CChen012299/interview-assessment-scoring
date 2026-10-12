"""Scoring logic for sectioned assessments.

Turns a student's submitted answers into per-section scores, a weighted overall
percentage and a pass/fail verdict. The pass bar is ``MASTERY_THRESHOLD`` from
``src.config``, applied both overall and to every section individually.
"""

import math
from typing import TypedDict

from src.config import MASTERY_THRESHOLD


class SectionScore(TypedDict):
    """Score for a single section; matches ``SectionScoreResponse`` in ``src.models``."""

    id: str
    name: str
    points_earned: int
    points_possible: int
    percentage: float
    passed: bool


class ScoreResult(TypedDict):
    """Full scoring result returned by :func:`calculate_score`."""

    section_scores: list[SectionScore]
    overall_percentage: float
    passed: bool


def _normalize_answer(answer: str) -> str:
    """Normalize an answer string so equivalent answers compare equal.

    Matching is case-insensitive and ignores leading/trailing whitespace. Internal
    whitespace is left alone, so "main  idea" does not match "main idea".

    Args:
        answer: Raw answer text, either submitted or correct.

    Returns:
        The answer stripped of surrounding whitespace and case-folded.
    """
    # casefold() is a more aggressive lower() that also handles Unicode cases
    # such as German "ß" -> "ss", so it is the recommended way to compare text
    # case-insensitively.
    return answer.strip().casefold()


def _meets_threshold(percentage: float) -> bool:
    """Return whether a percentage meets the mastery threshold.

    A plain ``>=`` is not enough: a weighted sum of floats can land a hair below
    the threshold even when every section is exactly at it (for example
    ``0.8 * 0.3 + 0.8 * 0.7 == 0.7999999999999999``). ``math.isclose`` treats
    those rounding-error misses as meeting the bar.

    Args:
        percentage: A score between 0.0 and 1.0.

    Returns:
        True if the percentage is at or (within float tolerance) equal to
        ``MASTERY_THRESHOLD``.
    """
    return percentage >= MASTERY_THRESHOLD or math.isclose(percentage, MASTERY_THRESHOLD)


def _score_section(section: dict, normalized_answers: dict[str, str]) -> SectionScore:
    """Score one section against the student's (already normalized) answers.

    Args:
        section: Section dict with ``id``, ``name`` and ``questions`` (a mapping of
            question_id -> correct answer). ``weight`` is not used here.
        normalized_answers: question_id -> submitted answer, already passed
            through :func:`_normalize_answer`.

    Returns:
        The section's points earned/possible, percentage and pass flag.

    Raises:
        ValueError: If the section has no questions, because its percentage would
            be undefined (0 / 0) and any pass/fail verdict would hide bad data.
    """
    questions: dict[str, str] = section["questions"]
    if not questions:
        raise ValueError(f"Section {section['id']!r} has no questions")

    # Iterate over this section's questions only: unanswered questions get None
    # from .get() and never match, and answers to questions outside the section
    # are never looked at, so both docstring rules come for free.
    points_earned = sum(
        1
        for question_id, correct_answer in questions.items()
        if normalized_answers.get(question_id) == _normalize_answer(correct_answer)
    )
    points_possible = len(questions)
    percentage = points_earned / points_possible

    return SectionScore(
        id=section["id"],
        name=section["name"],
        points_earned=points_earned,
        points_possible=points_possible,
        percentage=percentage,
        passed=_meets_threshold(percentage),
    )


def calculate_score(
    submitted_answers: dict[str, str],
    sections: list[dict],
) -> ScoreResult:
    """Score a student's submitted answers across a sectioned assessment.

    Each section has a weight and its own set of questions. The student must
    meet the mastery threshold both overall (weighted) and in each section
    individually to pass.

    Args:
        submitted_answers: maps question_id -> student's answer string
        sections: list of section dicts, each with:
            - id        (str):            section identifier
            - name      (str):            display name
            - weight    (float):          contribution to overall score
                                          (all weights sum to 1.0)
            - questions (dict[str, str]): maps question_id -> correct answer string

    Returns:
        A dict with:
            section_scores     (list): one entry per section, each with:
                - id               (str)
                - name             (str)
                - points_earned    (int)
                - points_possible  (int)
                - percentage       (float): 0.0 to 1.0
                - passed           (bool):  True if percentage >= MASTERY_THRESHOLD
            overall_percentage  (float): weighted average across all sections
            passed              (bool):  True only if
                                         overall_percentage >= MASTERY_THRESHOLD
                                         AND every individual section passed

    Raises:
        ValueError: If any section has no questions.

    Rules:
        - Questions not answered by the student count as incorrect
        - Answers submitted for questions not in any section are ignored
        - Comparison is case-insensitive and ignores leading/trailing whitespace
        - An empty submission is valid and scores 0 in all sections
        - Section weights are guaranteed to sum to 1.0
    """
    # Normalize each submitted answer once up front rather than once per
    # comparison inside every section.
    normalized_answers = {
        question_id: _normalize_answer(answer)
        for question_id, answer in submitted_answers.items()
    }

    section_scores = [_score_section(section, normalized_answers) for section in sections]

    # section_scores is built in the same order as sections, so zip pairs each
    # score with the weight of the section it came from.
    overall_percentage = sum(
        score["percentage"] * section["weight"]
        for score, section in zip(section_scores, sections)
    )

    return ScoreResult(
        section_scores=section_scores,
        overall_percentage=overall_percentage,
        passed=_meets_threshold(overall_percentage)
        and all(score["passed"] for score in section_scores),
    )
