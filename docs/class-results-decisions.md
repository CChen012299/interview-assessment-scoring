# Class assessment results: design decisions and thought process

**Feature:** `GET /classes/{class_id}/assessments/{assessment_id}/results`
**Date:** 2026-10-09
**Companion:** `class-results-plan.md` (the step-by-step implementation plan; it refers to
the decision IDs below)

This document records what was decided, which alternatives were weighed, and why. It is
the raw material for the "Class results feature", "Tradeoffs" and "Working with AI"
sections of `NOTES.md`, and for the live-session walkthrough.

**About the voice:** section 2 is drafted in *your* voice ("I" is you, "Claude" is the AI
assistant), so it can feed NOTES.md directly. Edit it freely. Text in **[brackets]** marks a
reason only you can give; it was left blank rather than invented.

**Current state, in one line:** a new endpoint backed by a pure summarizer module, 16 lean
tests in the existing test style, and no coverage tooling. Decisions that were made and
later withdrawn are kept and marked **Withdrawn**, because the reasons are part of the
story.

---

## 1. The problem as understood

**The ask.** The take-home brief asks: "Add what's needed so a teacher can see each
student's result for an assessment: who passed, who didn't, and enough detail to understand
where students are struggling, such as how they performed across the different sections of
the assessment." `python/README.md` narrows it: "Extend the API so it also returns each
student's latest score for a given assessment. Design the API shape yourself."

**The starting point.** `GET /classes/{class_id}` returns only a roster: id, name, teacher
and a list of student `{id, name}`. Scores live in the `submissions` table and can only be
read one student at a time through `GET /students/{student_id}/scores`, with every
assessment mixed together.

For one class, a teacher's screen would need one roster call plus one call per student,
then filtering and joining on the client. This is the "N+1" pattern: one request for the
list, then N more, one per item.

**The core insight.** The feature is a server-side join of *roster × submissions for one
assessment*, plus a summary. It only reads data. Nothing about submitting or scoring
changes.

**What the seed data tests.** The seed (`data/seed.sql`) is clearly built to probe the hard
cases:

| Case in the seed | Why it matters |
|---|---|
| Sam Rivera (Room 12A) has no submission for Grade 3 Reading | A naive join silently drops them, and "not submitted" must not look like 0% |
| Jamie Lee (Room 12C) scored 85% overall and still failed (Comprehension 3/4 = 75%) | The overall percentage cannot explain the verdict; the section breakdown is required |
| Riley Johnson (Room 12B) scored 0/3 on Vocabulary | A real 0% must count in averages; it is a score, not missing data |
| Alex, Sam, Casey and Riley are each in two classes | A submission belongs to a student, not a class; it must appear in both class views |
| Nobody in Room 12B has taken Grade 3 Math | Must return 200 with every student "not submitted" and every section still listed |
| Seed percentages are pre-rounded (0.333, 0.667) | Averages mixing seed and live data differ slightly; tests use tolerances |

---

## 2. How the design evolved (draft, in your voice)

**Step 1: break the requirement down before designing anything.** Before writing code, I
asked Claude for a detailed breakdown of what Part 2 asks for. Reading the code turned up
four constraints that are not in the brief:

- `tests/test_api.py::test_get_class_returns_students_without_scores` requires the plain
  roster response to contain no `scores` or `submissions` keys. Bolting results onto that
  response unconditionally is therefore ruled out.
- `submissions.student_id` has no foreign key, and the tests submit for made-up ids such
  as `student-abc`. Results have to be driven by the roster, not by the submissions table.
- Section scores are stored as JSON text. SQLite's `json_each` could unpack them in SQL,
  but doing the summary in Python keeps it in a pure, unit-testable module (D12).
- A roster LEFT JOIN submissions query has a trap: putting the assessment filter in
  `WHERE` instead of `ON` silently drops students who haven't submitted. D13 avoids the
  trap entirely.

**Step 2: my first proposal, and the pushback I asked for.** I asked Claude to act as a
senior developer and push back on weak ideas. I proposed `GET /classes/{class-id}/summary`,
with the summary computed in its own small module.

- **Kept:** a new endpoint rather than extending the roster endpoint, and a separate
  module for the summary logic.
- **Changed after the pushback:**
  1. **My proposal had no assessment in it.** Sections differ between assessments, so a
     summary across all of them is either meaningless (Vocabulary vs Computation) or grows
     without limit. The assessment became part of the path (D1, D3).
  2. **"Summary" named the wrong thing.** The main ask is per-student results; the summary
     is one block inside the response (D2).
  3. **"Its own module" only satisfies the Single Responsibility Principle if the module is
     pure,** with no database or HTTP code (D12).
  4. **`{class-id}` became `{class_id}`.** FastAPI maps path parameters to Python argument
     names, and the existing routes use `{class_id}`.

**Step 3: how to represent "not submitted".** I asked for my options with pros and cons.
Claude laid out five (D4), and I chose a `status` field plus a nested, nullable
`submission` that reuses the existing `SubmissionResponse`.

**Step 4: what the summary means.** I decided that averages exclude students who haven't
submitted (D7), and that the section list comes from the `sections` table (D10).

**Step 5: tests, first version: 100% coverage.** I first asked for new tests in the
existing style, 100% coverage, and a plan small enough for a less capable model to execute.
Claude measured the baseline before planning:

- `src/` was at 93%.
- `GET /assessments/{assessment_id}` had never been tested.
- Part 1's empty-section `ValueError` was untested.
- `test_submit_returns_500_before_scoring_implemented` can never pass again.

I scoped coverage to the new feature code **[your reason]**, kept the stale test failing
and documented **[your reason; for example, I treat the provided suite as the grader's
specification]**, and put the gate in the standard test command **[your reason]**. That
version became D20 and D21, both later withdrawn (step 8).

**Step 6: prototype before planning.** Claude built everything in a scratch copy and ran it
before writing the plan. That changed the design in four ways:

- **100% coverage is not the same as tested decisions.** With every test of the "no data,
  so the average is None" path deleted, the module still reported 100%. coverage.py
  counts a one-line `x if c else y` as covered once the line runs.
- **Docstrings leak into the public API docs.** FastAPI shows docstrings on `/docs`
  (through OpenAPI, the machine-readable API description it generates). D30 records what
  was done about it.
- **Practical traps for whoever executes the plan:**
  - Every existing file except `src/scoring.py` has Windows (CRLF) line endings in the
    working tree, because git's `core.autocrlf` is on.
  - An old Docker image already exists, so tests must run with `--build`.
  - Three over-long lines already exist in `database.py`.
  - A `python-api` container was already running on port 8000, so the smoke test must not
    restart or stop it.

**Step 7: verify the plan itself, adversarially.** Claude checked the plan four ways:

1. **Mechanically.** A script applied the plan's code blocks to a fresh copy of the repo,
   and the result matched the prototype file for file. A phase-by-phase run recorded the
   real test counts, which became the plan's expected values.
2. **By execution.** Smaller models (Claude Haiku and Claude Sonnet) executed earlier
   versions of the plan end to end in isolated scratch repos, and every Verify step
   matched.
3. **By review.** Four independent reviewers found real problems:
   - D16 claimed something false.
   - Several decisions could be reversed without any test failing.
   - The `/docs` leak was only partly fixed.
   - The smoke test raced the server's startup.
   - The line-ending note was wrong.

   All of these were fixed, and a second review confirmed the fixes.
4. **By mutation.** Claude deliberately reversed seven decisions in the code to see which
   ones the tests catch (D22).

**Step 8: I dropped the coverage requirement and trimmed the tests.** **[Your reason; for
example, a coverage gate was more machinery than a 2-hour take-home needs, and the stale
test meant it couldn't fail the run anyway.]**

- **Removed:** all coverage tooling, so `requirements.txt`, the Dockerfile and the compose
  file are no longer touched. Also removed: the two tests for the old
  `GET /assessments/{id}` route, which existed only for coverage, and the edge-case tests
  added after the review.
- **Kept:** a lean core of 16 tests (8 unit, 8 API), restyled to match the existing tests
  exactly.
- **Trade-off, measured:** of the seven decision reversals, the lean suite catches the
  three core ones (0% treated as missing, the verdict recomputed instead of read, and
  non-submitters counted as 0). It no longer catches the other four (D22).

---

## 3. Decision log

### API shape

**D1. A new nested resource: `GET /classes/{class_id}/assessments/{assessment_id}/results`.**

- **Options:**
  - extend `GET /classes/{class_id}` with `?assessment_id=`
  - `GET /classes/{class_id}/summary` (my first proposal)
  - `GET /classes/{class_id}/results?assessment_id=` with the parameter required
  - the assessment-first `GET /assessments/{id}/results?class_id=`
- **Why:**
  - Both ids are required and together identify the resource, so both belong in the path.
  - An unknown class and an unknown assessment each get a clean 404.
  - One URL always has one response shape.
  - The roster contract, and the test that guards it, are untouched.
- **Trade-off:** the URL implies a class↔assessment "assignment" relationship the schema
  doesn't have (section 5). The query-parameter version would make an "all assessments"
  view easier later (make the parameter optional), but building for that now would be
  speculative.

**D2. Name it "results", not "summary".** The main content is per-student results. The
summary is derived from them and sits inside the response as `summary`.

**D3. One assessment per request.** Sections differ per assessment, so only within one
assessment do all students share the same sections. A multi-assessment view is just a
list of these responses (section 6).

**D14. 404 semantics.**

- An unknown class gives `404 "Class not found"`, and it is checked first. An unknown
  assessment gives `404 "Assessment not found"`.
- These reuse the existing detail messages, so clients see consistent errors across
  endpoints.
- A real class and assessment with zero submissions gives **200**, with every student
  `not_submitted`. "Nobody has taken it yet" is a valid answer, not an error.
- Each 404 is tested. Which one wins when both ids are unknown is not tested (lean suite).

**D15. Ordering.** Students come in roster order, by student id (what
`get_class_with_students` already returns). Sections come in assessment order, by section
id (what `get_assessment_detail` returns). This is deterministic, so tests can compare
lists exactly.

### Response shape

**D4. Students without a submission: a `status` enum plus a nullable nested `submission`.**

| Option | Verdict | Reason |
|---|---|---|
| Sentinel values (0%, false) | Rejected | Looks the same as a real empty submission (which is valid and scores 0) and corrupts averages: Room 12A's Vocabulary average would drop from 83.3% to 66.7% |
| Two lists (`students`, `not_submitted`) | Rejected | Splits the roster; the client must merge and re-sort, which is the join this endpoint exists to remove |
| Flat nullable fields (`passed: null`) | Rejected | Creates a three-state boolean: `if (!s.passed)` treats null as failed. It also allows invalid combinations such as an overall score with `passed: null` |
| Nested nullable `submission` | Good | One null check decides everything; inside it, every field is non-null |
| **`status` + nested `submission`** | **Chosen** | "Who passed" is one top-level field, filtering is one equality check, the values appear in `/docs`, and the summary counts become a `Counter` over `status` |

The name `not_submitted` states only a fact. Words like "missing" or "overdue" would imply
a due date or an assignment the data does not have.

**D5. `status` is a Pydantic `@computed_field` derived from the stored verdict.**

- It is computed from `submission`, never stored separately, so the two can never
  disagree.
- It reads the stored `passed` flag instead of recomputing against `MASTERY_THRESHOLD`.
  The verdict therefore reflects the rule that applied when the student submitted, and
  editing `config.py` later doesn't quietly change history.
- A unit test with an 85% submission that still failed pins this; it is the only case
  where recomputing would give a different answer.
- `@computed_field` serializes into the JSON and appears in the OpenAPI schema as
  read-only (verified).

**D6. The nested object reuses the existing `SubmissionResponse`.** The class view and
`GET /students/{id}/scores` share one shape, which is DRY (Don't Repeat Yourself). A client
that already renders a student's scores can reuse that component. The cost is two
redundant fields, `student_id` and `assessment_id`, which is minor.

**D9. An average of nothing is `null`, not 0.** Zero would claim the class scored 0%. The
response also carries `submitted_count`, so a client can tell "no data" from "low scores".

**D11. Count fields end in `_count`** (`passed_count`, `submitted_count` and so on).
`passed` is already a boolean on submissions and section scores. Reusing it as an integer
in the summary would invite mix-ups.

**D18. Floats are returned unrounded** (e.g. `0.83325`), consistent with every existing
endpoint, which returns raw percentages. Rounding is presentation, and that's the client's
job.

**D30. Docstrings and the public `/docs` page.**

- FastAPI shows a route's docstring on `/docs`. The route's docstring therefore ends its
  public part with `\f` (a form feed, written as the two-character escape in source), the
  cut-off marker FastAPI supports. The Google-style Args/Returns/Raises sections stay
  visible to code readers but not to API consumers.
- Implementation notes that had leaked into `/docs` moved into code comments: the
  `StrEnum` explanation, and the "computed rather than stored" rationale for `status`.
- **Accepted trade-off:** each model's Google-style `Attributes:` block still appears as
  that schema's description on `/docs`. The text is accurate and the user's standard
  requires those docstrings. The alternative, per-field `Field(description=...)`, would
  duplicate every description.

### Summary semantics

**D7. Averages exclude students who haven't submitted.** A missing submission is "no data",
not a zero. Counting Sam as 0 would pull Room 12A's overall average from 85.8% down to
68.7%, and would make the class look weak on material most students haven't attempted.
`submitted_count` sits next to every average so the denominator is visible.

**D8. Averages are the mean of each student's percentage, not pooled points.** The
teacher's question is "how did my students do?", so each student counts once.

- **Section averages:** the two methods agree whenever a section's `points_possible` is
  the same for every submission, which is always true unless the assessment was edited
  after some students had submitted.
- **The overall average:** pooling points would be wrong, because it ignores section
  weights. In Room 12A, pooled points give 24/28 = 0.857, while the mean of the students'
  weighted overall scores is 0.858. They differ because the sections have different
  weights (0.4 and 0.6) and different numbers of questions.

`statistics.fmean` is used (a fast float mean). It raises on an empty list, hence D9.

**D10. The section list comes from the assessment definition (the `sections` table).**

- If it came from submissions, a class with no submissions would show no sections at all.
  The prototype showed exactly that for Room 12B on Grade 3 Math, and a test now pins it.
- Stored section scores are matched to the definition by section **id**, not name. A
  stored section that is no longer in the definition is ignored.
- A submission missing a section is left out of that section's counts rather than counted
  as 0, so stale snapshots degrade gracefully.
- The id-based matching and the snapshot handling are not tested (lean suite).

### Code structure

**D12. Layering: a pure module, with the route doing the coordinating.**

| Layer | Owns |
|---|---|
| `src/database.py` | SQL only: the new query, plus the existing roster and assessment lookups |
| `src/class_results.py` (new) | Pure functions: roster + submissions → student results; student results + sections → summary |
| `src/models.py` | Response shapes, including the computed `status` |
| `src/app.py` | The route: 404s, calling the database layer, calling the module, returning the response |

This mirrors the existing `submit` route, which fetches from the database, calls the pure
`calculate_score`, and saves. The module never imports `MASTERY_THRESHOLD` (D5), and it can
be unit-tested with hand-built objects and no database.

**D13. Reuse the existing lookups, and let the roster drive the merge.**

- The route gets the roster from the existing `get_class_with_students`, and the
  assessment and its sections from `get_assessment_detail`. Both also answer the 404
  questions. That's DRY.
- The only new query fetches submissions with an inner join on `class_students`.
- `build_student_results` walks the roster and looks each student up in a dict. Students
  without a submission appear naturally, and the LEFT JOIN trap never arises.
- **Correctness comes from the roster-driven merge,** which a unit test pins. The JOIN is
  an efficiency filter: it keeps the query from loading every student's submissions for
  the assessment. A broken JOIN would not change any response, so no test would notice
  (lean suite).
- **Trade-off:** the endpoint makes three database calls, which is five small SELECTs over
  three separate connections, with no shared read snapshot. On a local SQLite file this is
  negligible. At scale, use one connection, or one query, plus an index on
  `submissions(assessment_id, student_id)`.

**D16. `ORDER BY rowid` makes the result deterministic. That is all it does.**

- `save_submission` keeps one row per student and assessment by checking first and then
  updating or inserting. Nothing in the schema enforces that.
- If a race ever created duplicates, the class view would deterministically show the
  highest-rowid row. But `save_submission`'s own lookup has no `ORDER BY`, and in
  practice it updates the *oldest* duplicate. A later resubmission would land on a row
  this view doesn't show, so the teacher would keep seeing a stale result. A reviewer
  reproduced exactly this.
- With duplicates and no timestamps, no ordering is "right". The real fix is a UNIQUE
  index on `(student_id, assessment_id)` plus `INSERT ... ON CONFLICT DO UPDATE` (section
  5). That is a correctness fix, not a nice-to-have.
- Detecting and logging duplicates in this query was considered and rejected. It would
  patch a symptom with extra branches, while the index removes the cause.
- No test pins this ordering (D22).

**D17. Extract `_row_to_submission`.**

- The row-to-model conversion that `get_submissions_for_student` did inline is now one
  private helper, shared by both queries (DRY).
- It's a pure refactor, but the provided tests barely look inside a converted submission:
  one returns an empty list, and the other checks only the count and `assessment_id`.
- The plan therefore adds a direct check at Phase 1 (one seeded submission's id, scores
  and section points). The new API tests then read converted fields through the endpoint.

**D24. Docstrings and type hints on new source code only.**

- New functions and classes in `src/` follow the user's standards: Google-style
  docstrings, full type hints, and `Optional[T]` for values that can be None.
- Existing undocumented code is not retrofitted, so the diff reviewers read contains only
  the feature.
- The new database function keeps `db_path: str | Path`, matching its neighbors. That is a
  union of types, not a nullable value, so it doesn't conflict with the `Optional[T]` rule.

**D27. The local variable is `class_`.** `class` is a Python keyword. PEP 8, Python's style
guide, recommends a trailing underscore over a misspelling such as `klass`.

**D28. The route function is `get_class_results`.** Its name must not shadow any imported
database function. Otherwise the route would replace that import and end up calling itself.

### Testing

**D19. A lean test suite in the existing tests' style.**

- **Two new files; no provided test file is edited.** 16 tests in total:

  | File | Tests | What it tests |
  |---|---|---|
  | `tests/test_class_results.py` | 8 | Unit tests of `status`, `build_student_results` and `summarize_class_results`, using hand-built objects and no database |
  | `tests/test_class_results_api.py` | 8 | API tests against seed data, including one submit-then-read end-to-end test |

- **Lean by choice.** The tests cover the main paths plus the core decisions: the stored
  verdict, averages that exclude non-submitters, a 0% score counting, sections listed
  with zero submissions, and the end-to-end wiring. **[Your reason for the lean core.]**
- **Style copies the existing tests exactly.** That means plain functions, descriptive
  `test_<subject>_<behavior>` names, module-level test data, comments that show the
  arithmetic, `pytest.approx` for floats, the shared `test_client` fixture, literal URLs,
  and the status code asserted before the body.
- **The user's general docstring and type-hint rules do not apply to tests here.** There
  are no module docstrings, and no docstrings or type hints on test functions or the two
  small helpers. The user's specific instruction (unit tests "need only comply with the
  standard of the previous unit tests") outranks the general rule.

**D20. Withdrawn: a 100% coverage gate in `docker compose run test`.**

- **What it was:** pytest-cov with branch coverage, configured in `.coveragerc`, run by
  the standard test command, failing below 100% on every file the feature touched.
- **Why it was dropped:**
  - It needed changes to `requirements.txt`, the Dockerfile and the compose file.
  - It needed two extra tests for an old route the feature doesn't change (D21).
  - While the stale test fails (D23), the run exits non-zero anyway, so the gate could
    only print a verdict; it could never fail the run.
  - Prototyping showed that 100% coverage doesn't prove decisions are tested: the
    mutation check (D22) is a better measure.
- **[Your reason, if different.]**

**D21. Withdrawn: tests for the pre-existing `GET /assessments/{assessment_id}`.** These
existed only so `app.py` could reach 100%. Without the gate (D20), they're out of scope.

**D22. What the tests pin, and what they deliberately don't.** To check which *decisions*
the tests protect, not just which lines run, seven decisions were deliberately reversed in
the code (mutation testing). Results for the lean suite:

| Reversal injected | Decision | Caught by the lean suite? |
|---|---|---|
| Treat a 0% score as missing data | D4, D7, D9 | **Yes:** `test_get_class_results_averages_count_a_zero_score_as_a_score` |
| Recompute pass/fail from the overall percentage | D5 | **Yes:** `test_status_uses_stored_verdict_even_when_overall_meets_threshold` |
| Count non-submitters as 0 in averages | D7 | **Yes:** four tests, the two averages tests and the two "no submissions" tests (unit and API) |
| Check the assessment before the class | D14 | No |
| Drop the roster JOIN from the query | D13 | No (the response wouldn't change; only efficiency) |
| Match stored sections by name instead of id | D10 | No |
| Keep the lowest-rowid duplicate instead of the highest | D16 | No (no ordering is "right"; see D16) |

An earlier, fuller suite of 38 tests caught six of the seven. The lean suite trades the
four "no" rows for fewer tests (step 8).

`_mean_or_none` and `StudentResult.status` keep plain `if` statements. These were
originally chosen so branch coverage could see both outcomes; with no coverage tooling
they are simply the readable choice.

**D23. The stale test stays failing and is documented.**
`test_submit_returns_500_before_scoring_implemented` asserts behavior from before Part 1,
so it can never pass. I chose not to edit it. **[Your reason; for example, I treat the
provided suite as the grader's specification.]** As a result:

- Every run shows `1 failed` and exits non-zero.
- The README states that this is expected and points to `NOTES.md.template`, which must
  explain it, because the provided README text still says all 16 tests should pass.
- An option not taken: skip that one test in the compose command with
  `--deselect tests/test_api.py::test_submit_returns_500_before_scoring_implemented`. The
  provided file stays untouched and the run goes green, but the test is hidden in
  configuration.

**D25. Withdrawn: adding `pytest-cov` to `requirements.txt`.** No longer needed without the
gate (D20).

### Documentation and scope

**D26. Authorization is out of scope, and that's stated explicitly.** Anyone can read any
class's results. Real student records fall under FERPA (the Family Educational Rights and
Privacy Act, the US law governing access to student education records), so a production
version must check that the caller teaches the class.

**D29. Document the endpoint in `python/README.md`.** The README is the API reference
reviewers read, so the new endpoint gets a short entry there. It also gets a note that the
stale test is expected to fail, plus the `--build` tip. The provided exercise text ("What
to implement", "All 16 should pass") is the brief, so it is left as written.

---

## 4. Verification summary

| Check | Result |
|---|---|
| Full suite on the prototype | 31 passed, plus 1 expected failure (the stale test) |
| flake8 (max line length 92) | Clean on all new code; 3 pre-existing E501 lines left alone |
| Plan's code blocks applied to a fresh copy | Identical to the prototype |
| Test count after each phase | Matches the plan's overview table (15, 15, 15, 15, 23, 23, 23, 31) |
| Every Verify command in the plan | Prints exactly the expected output |
| Mutation testing | Lean suite catches 3 of 7 decision reversals, the three core ones (D22) |
| Smaller models executing the plan | Earlier versions: Haiku and Sonnet, every Verify step matched |
| Smoke test on a real server | 200 with the expected summary; 404 for an unknown class |

---

## 5. Known limitations and what I'd do next

- **Authorization** (D26): only the teacher of a class, or an admin, should see its
  results.
- **Enforce one submission per student and assessment.** Add
  `CREATE UNIQUE INDEX ... ON submissions(student_id, assessment_id)` and make
  `save_submission` an `INSERT ... ON CONFLICT DO UPDATE`. This closes the race behind
  D16, which today can hide a resubmission.
- **Decisions not pinned by tests** (D22): the 404 order, the roster JOIN, id-based
  section matching, and duplicate ordering. Add tests if any of these start to matter.
- **There's no class↔assessment assignment table.** "Not submitted" can't be told apart
  from "never assigned", and every assessment looks valid for every class. An
  `assignments` table would make `not_submitted` mean "assigned and outstanding", and
  would let the API return 404 for unassigned pairs.
- **Resubmission overwrites, with no timestamps.** "Latest score" is only ever "the only
  score", and progress over time can't be shown. Storing submission history with
  timestamps would enable trends.
- **Question-level insight is impossible today,** because answers are not stored. Saving
  them would allow "everyone missed q-006" analysis, which is the next level of "where are
  students struggling".
- **The stale 500 test** should eventually be removed or rewritten, so the run can go
  green.
- **Dependencies are unpinned,** and the test client already warns that its `httpx`
  backend is deprecated. A lockfile would make builds reproducible.
- **Part 1's empty-section `ValueError` has no test.**
- **Pre-existing lint:** three over-long lines in `database.py`, and no module docstrings
  on the original modules.

---

## 6. How the design accommodates likely extensions

| Likely ask | How it fits |
|---|---|
| "Show all assessments for a class" | `GET /classes/{class_id}/results` returns a list of today's response blocks, one per assessment, calling the same `build_student_results` and `summarize_class_results` per assessment |
| "Only show failing students" | `?status=failed`; the enum makes it one equality filter |
| "School-wide results for an assessment" | `GET /assessments/{assessment_id}/results` reuses the pure module over a different roster |
| "Add an `excused` status" | A new enum value and one more branch in `status`; clients must treat unknown statuses gracefully |
| "Per-question breakdown" | Needs stored answers (section 5), then a new pure function next to `_summarize_section` |
| "Trends over time" | Needs submission history (section 5), then a summary per time window |

---

## 7. Mapping to NOTES.md

- **How the service works:** section 1 (starting point), plus the request flow in D12.
- **Class results feature:** D1–D5, D7, D10 and D12, with the reasoning from section 2.
- **Tradeoffs and what I'd do next:** D13, D16, D19, D22, D23 and D30, plus section 5.
  D20 is a good "considered and dropped" story.
- **Working with AI:** section 2 is the collaboration history:
  - where my first proposal was kept, and where it was pushed back on
  - my decisions on coverage, the stale test, and the lean suite
  - what verification caught: the false D16 claim, and the reversible decisions
  - Fill in the **[bracketed]** reasons before using it.
