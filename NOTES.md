# Notes

My first thought/approach to this was to have GET /classes/{class_id} return a detailed
summary for that class, including "what's needed so a teacher can see each student's result
for an assessment", but because one of the tests,
test_get_class_returns_students_without_scores, asserts to make sure there are no "scores"
or "submissions" in that endpoint, I opted for a different route. In my original vision, the
class roster would be returned by a different call, like GET /classes/{class_id}/students

## How the service works

> *Describe the end-to-end flow in your own words: what happens from HTTP request to stored
> result*

A FastAPI app over one SQLite file. `app.py` holds the routes (validation, 404s),
`database.py` all SQL, `scoring.py` the pure scoring function, and `models.py` the Pydantic
request and response shapes. On startup `seed.sql` runs idempotently
(`CREATE TABLE IF NOT EXISTS`, `INSERT OR IGNORE`), so restarts keep new submissions.

A submission (`POST /assessments/{assessment_id}/submit`) goes through six steps:

1. **Validate:** Pydantic parses the body into `SubmitRequest` (422 if no `student_id`).
2. **Look up** the assessment's sections and answer key (404 if unknown).
3. **Reshape** them into plain dicts, so scoring knows nothing about the database.
4. **Score** with `calculate_score`: passing needs 80% overall **and** in every section.
5. **Store:** `save_submission` updates the student's row for that assessment or inserts
   one, with section scores stored as JSON and `passed` as 0/1.
6. **Respond** with the same values as a `SubmissionResponse`.

**Worked example:** the README's curl sends three correct answers for Maya Chen. Vocabulary
is 2/3 (66.7%) and Comprehension 1/4 (25%), so overall is 0.4 × 0.667 + 0.6 × 0.25 = 41.7%
and she fails. She already has a seeded row, so step 5 updates it and her seeded 100% is
gone: "latest score" really means "only score". Read endpoints only query and reshape
stored data; nothing is re-scored.

## Scoring function

> *How did you approach implementing calculate_score? Any edge cases that gave you pause?*

I treated the docstring and `tests/test_scoring.py` as the spec and split the work into
small helpers: `_normalize_answer`, `_meets_threshold` and `_score_section`. Answers are
normalized once (trim + case-fold), and each section walks only its own questions, so
unanswered questions count as wrong and stray answers are ignored for free. The overall
score is the weighted sum of section percentages.

Edge cases that gave me pause:

- **Float rounding:** sections exactly at 0.8 can sum to 0.7999…
  (`0.8*0.3 + 0.8*0.7 == 0.7999999999999999`), so the threshold check allows float
  tolerance (`math.isclose`).
- **A section with no questions** (0/0) raises `ValueError` rather than invent a verdict.
  Through the API that surfaces as a 500 and nothing is saved. Untested.
- **85% overall can still fail** if one section is under 80%: Jamie Lee scores
  0.4 × 100% + 0.6 × 75% = 85% but fails Comprehension, which is why the class view shows
  sections.
- **Caveats:** no provided test pins the case, whitespace or stray-answer rules. And an
  assessment with **zero sections** doesn't raise: the empty sum gives 0%, so it fails,
  which is inconsistent with the empty-section `ValueError`.

## Class results feature

> *What did you build? Why did you structure it the way you did? If you chose to extend an
> existing endpoint vs. create a new one, explain that choice.*

**Built:** `GET /classes/{class_id}/assessments/{assessment_id}/results`. The assessment is
in the path because sections differ between assessments, so a class summary only makes
sense for one; each id also gets a clean 404.

It returns every roster student with a `status` (`passed`, `failed`, `not_submitted`) and
their `submission` (reusing the existing `SubmissionResponse`) or `null`, plus a `summary`:
status counts, the average overall percentage, and per-section submitted and passed counts
and averages. Room 12A on Grade 3 Reading: 4 of 5 submitted, 2 passed, 85.8% average.

**A new endpoint, not an extended one.** As above, the roster test rules out adding results
to `GET /classes/{class_id}`. An optional `?assessment_id=` there would keep it green, but
one URL would return two shapes, and my first proposal (`/summary`) had no assessment in
it. The nested path requires both ids and leaves the roster contract and its test intact.

Rules that shaped it:

- **The roster drives the output,** so non-submitters appear and submissions from students
  outside the class are ignored.
- **`status` reads the stored verdict** instead of re-scoring, so changing the threshold
  later doesn't rewrite history.
- **Averages skip non-submitters.** "No data" isn't zero: counting Sam as 0 would drop Room
  12A from 85.8% to 68.7%. A real 0% does count, and no submitters means `null`.
- **Averages are a mean of student percentages, not pooled points.** Each student counts
  once, and pooling ignores section weights: Room 12A pools to 24/28 = 85.7%, against the
  85.8% mean.
- **Sections come from the assessment definition,** so they're listed before anyone submits.

**Structure** mirrors `submit` and `calculate_score`: the route fetches and handles 404s
with the existing lookups, and a new pure module, `class_results.py`, does the logic, so
it's unit-tested without a database. `database.py` gains one roster-filtered query and a
shared row-to-model helper. 16 new tests: 8 unit and 8 API, including one that submits and
then reads the results back.

## Tradeoffs and what I'd do next

> *What tradeoffs did you make? What would you tackle with more time?*

**Tradeoffs**

- **A new endpoint over extending the roster one:** one more URL, but the roster contract
  and its test stay intact.
- **Stored verdicts over re-scoring:** history stays stable, but a fix to the scoring logic
  wouldn't correct old verdicts without a backfill.
- **Three database lookups per request** (roster, assessment, submissions), each on its own
  connection: negligible on local SQLite, but one query plus an index would scale better.
- **Lean tests over a 100% coverage gate,** which needed changes to the requirements,
  Dockerfile and compose file: too much machinery here. Of seven decisions reversed on
  purpose, the lean suite catches the three core ones; the 404 order, the roster JOIN,
  id-based section matching and duplicate-row ordering are deliberately untested.
- **The stale `test_submit_returns_500_before_scoring_implemented` stays failing.** It
  asserts pre-Part-1 behavior, but I treat the provided tests as the spec, so I didn't edit
  or skip it.
- **Swapped `httpx` for `httpx2`:** the unpinned requirements had pulled in a Starlette
  version that deprecates `httpx`.

**With more time**

- **Authorization:** only the class's teacher should see results (student records fall under
  FERPA, the US Family Educational Rights and Privacy Act).
- **A `UNIQUE (student_id, assessment_id)` index plus an upsert,** since a duplicate row
  could hide a resubmission.
- **Submission history with timestamps and stored answers,** so a resubmission doesn't
  erase the old score (as in the README example) and teachers get trends and
  question-level insight.
- **An assignments table,** to tell "not submitted" from "never assigned".
- **Scoring tests** for the case, whitespace and stray-answer rules, and one consistent rule
  for empty sections and empty assessments.
- **Pin dependencies** and retire the stale test.

## Working with AI

> *How did you use AI tools? What did you prompt, what came back, what did you change and
> why? Think of this as a reflection on the collaboration, not a log.*

I used Claude Code as a pair programmer that explains its changes.

**Part 1.** Claude implemented `calculate_score` from the docstring and I reviewed it. It
also edited the provided tests; I rejected that, and "don't edit provided tests" became a
standing rule.

**Part 2.** I asked for a requirements breakdown first, which surfaced the test keeping
scores out of the roster response. I proposed `GET /classes/{class_id}/summary` and asked
Claude to push back like a senior developer. The new endpoint and separate module survived,
but the assessment moved into the URL, "summary" became "results", and the module had to be
pure. For non-submitters, I asked for options with pros and cons and chose `status` plus a
nullable `submission`.

I first asked for 100% coverage, then dropped it for a lean suite; Claude broke seven
decisions on purpose to show what the lean suite still catches (the three core ones). Claude
wrote a decisions log and a step-by-step plan, which reviews checked before I ran it phase
by phase, reviewing each phase before committing it. When I spotted a deprecation warning,
Claude traced the cause and I chose the fix.

**Takeaway:** Claude was best at finding constraints in the code, pushing back, and checking
its own work, but confident output still needed verifying: a review caught the plan
claiming more for `ORDER BY rowid` than it delivers when duplicate rows exist. The
decisions stayed mine.
