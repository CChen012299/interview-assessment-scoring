# Notes

##	How the service works end-to-end in your own words

When the app starts, it runs `data/seed.sql` against a SQLite file. The seed only uses `CREATE TABLE IF NOT EXISTS` and `INSERT OR IGNORE`, so restarting is safe, and since `data/` is a Docker volume, submissions stick around.

Submitting an assessment (`POST /assessments/{id}/submit`) goes like this:

1. Pydantic checks the body. No `student_id` means a 422.
2. It loads the assessment's sections and answer key. An unknown assessment means a 404.
3. It turns that into plain dicts and hands them to `calculate_score`, which is a pure function and never touches the database.
4. `save_submission` writes one row per student per assessment. If a row already exists it gets overwritten. Section scores are stored as a JSON blob.
5. The result goes back to the caller.

The read endpoints are simple lookups. One thing worth knowing for tests: `conftest.py` swaps `_DB_PATH` for a temp file, and that only works because every endpoint passes the path through. Forget that in a new endpoint and its tests quietly hit the real database.

A couple of things I noticed but left alone:

- **Overwrites can lose real work.** I tried it: if an empty submission comes in after Maya's 100% (a double-click, or hitting back and resubmitting), she's at 0% and the 100% is gone. There's also no timestamp, and two submits at the same moment can create duplicate rows, since nothing enforces one row per student.
- **Exact matching can end up testing English instead of math.** `"8"` for `"8 apples"` and `"3.50"` for `"$3.50"` both get marked wrong, even though a kid who answers `"8"` clearly knows the math. Whether that should count is a product call, not something I wanted to guess at in the scorer.

One dev fix I did make: compose only mounted `data/`, so `--reload` never picked up code changes and `docker compose run test` ran whatever was baked into the image. I mounted `src/` (and `tests/` for the test service) so edits show up right away.

## Scoring function

The main idea is to loop over each section's own questions instead of the answers the student sent. That takes care of two rules by itself: unanswered questions just score 0, and answers to questions that aren't on the test never get looked at. The overall score is the weighted sum, and to pass you need 80% overall and in every section.

Things that made me stop and think:

- **Floats right at the threshold.** With weights of 0.1, 0.7 and 0.2, a student who gets exactly 80% everywhere adds up to `0.7999999999999999`, which fails `>= 0.8`. I found a real case like that before changing anything, then added a tiny `1e-9` tolerance. It doesn't change the rule, it just absorbs the rounding noise, and the test fails without it.
- **What counts as the same answer.** The spec says case-insensitive, so I used `casefold()`, which catches a few things `lower()` misses (`"STRASSE"` vs `"straße"`). I also run NFC first, because `"café"` can be typed as one character or as an `e` plus an accent mark: same text, different bytes. I stopped there on purpose. Trimming spaces, or treating full-width digits from Chinese and Japanese keyboards as regular ones, changes what counts as correct, so like the `"8 apples"` thing, that's a product decision.
- **A section with no questions** would divide by zero, so I raise a `ValueError` that names the section instead.

Also, the test suite had a test that could never pass. `test_submit_returns_500_before_scoring_implemented` expects the stub to crash, so it fails the moment scoring works, which means the README's "all 16 should pass" can't be true. The C# suite has the same test, so I figured it was there on purpose. I swapped it for a test that sends the README's example request and checks the actual numbers, and added tests for the rules nobody had tested yet.

## Class results feature

`GET /classes/{class_id}/assessments/{assessment_id}/results`

I built this around what a teacher actually does after a test: chase the kids who haven't taken it, reteach the ones who didn't get there, and group students by what they're missing. The response is shaped around those three things.

```json
{
  "class_id": "class-001", "class_name": "Room 12A", "teacher_name": "Ms. Rivera",
  "assessment_id": "assess-001", "assessment_name": "Grade 3 Reading",
  "summary": {
    "passed": 2, "not_passed": 2, "not_submitted": 1,
    "average_overall_percentage": 0.858,
    "sections": [
      { "id": "sec-001", "name": "Vocabulary", "average_percentage": 0.833,
        "not_passed_student_ids": ["student-004"] },
      { "id": "sec-002", "name": "Comprehension", "average_percentage": 0.875,
        "not_passed_student_ids": ["student-003"] }
    ]
  },
  "students": [
    { "student_id": "student-003", "student_name": "Priya Patel", "status": "not_passed",
      "overall_percentage": 0.7,
      "section_scores": [ { "id": "sec-002", "name": "Comprehension", "points_earned": 2,
                            "points_possible": 4, "percentage": 0.5, "passed": false } ] },
    { "student_id": "student-005", "student_name": "Sam Rivera", "status": "not_submitted",
      "overall_percentage": null, "section_scores": [] }
  ]
}
```

**Why a new endpoint instead of adding to `GET /classes/{id}`?** "Who's in this class" and "how did this class do on this test" are different questions. The existing roster test even checks that there are no scores in it, which I took as a hint to leave it alone. Adding `?assessment_id=` would mean one URL returns two different shapes. And since you need both the class and the assessment, both go in the path. I also thought about `/assessments/{id}/results?class_id=`, which would suit a district comparing classes, but a teacher starts from their own class.

A few choices in the response:

- **Every student on the roster shows up**, even if they haven't submitted, because the teacher needs to see who's missing.
- **`status` is `passed`, `not_passed` or `not_submitted`**, rather than a `passed` field that's sometimes null. "Didn't take it" and "didn't pass" mean different things to a teacher, and a null is easy to read as false.
- **Section scores use the same shape** that `/students/{id}/scores` already returns.
- **The summary is small on purpose:** a count for each status, plus each section's average and `not_passed_student_ids`. That list is basically the small group for reteaching. In class-001, Vocabulary and Comprehension give you two different groups. I left out anything you could work out from other fields.
- **Pass/fail comes from what was stored at submit time**, so this view always matches what the student was told.

Under the hood it's five queries no matter how big the class is (class and roster, assessment and sections, and one new JOIN for everyone's submissions), so there's no query per student. The rollup lives in `src/class_results.py` as a pure function, same idea as `scoring.py`, and I pulled the row-to-model mapping into `_row_to_submission` so both submission queries share it. The seed data already covers the interesting cases. Jamie Lee is a good one: 85% overall but under 80% in Comprehension, so not passed.

## What tradeoffs you made, and what you'd do differently with more time

Tradeoffs I made:

- The summary is computed in Python on every request. That's fine for a classroom, not for a whole district.
- Assessments aren't assigned to classes, so `not_submitted` can't tell "hasn't taken it yet" from "was never given it," and you can ask for any assessment for any class.
- The summary uses the assessment's current sections. If a section got removed after students took the test, it drops out of the summary but still shows up in their scores.

With more time:

- **Keep every attempt** with a timestamp instead of overwriting. That fixes the lost-work problem, and benchmark data is really about growth over the year anyway. Until then, a unique constraint plus `INSERT ... ON CONFLICT` would at least stop the duplicates.
- **Per-question results.** "12 of 25 kids missed q-005" is a lot more useful to a teacher than a section average.
- **Access control.** Teachers should only see their own classes, and these are student records covered by FERPA.
- **Check assessments when they're created** (weights add up to 1, no empty sections), and set up real migrations.

## How you used AI tools

I used Claude Code to make a copy of the repo and give me an initial view of the repo so I can get a better understanding and where to begin. It took the first pass at everything: just running the pre-existing tests, wrote a basic boilerplate of the scoring which I built upon, expedited me with building out the new endpoint and writing some basic tests, and revised my notes, fixing some grammar, spelling and cleaning it up.

After that I had it do another pass looking for anything I might have missed, then any suggestions with some changes through the eyes of the people who'd actually use this, teachers and kids who are learning English. That's where the grouping list and the overwrite issue came from. Then I asked it to look for over-engineering, as one of the asks was not to handle every edge case or if I unintentionally went overboard. That pass undid some earlier work, pulling out full-width character handling, which contradicted my reasoning about whitespace, and it cut response fields that just repeated other fields. I also had it trim the comments and tests down to the ones that earn their place.

What it did best was check things instead of assuming them. It caught the test that could never pass, found a real failing float case before fixing anything, and wrote tests that fail if you undo the fix.
