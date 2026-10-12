# Class summary: design decisions and thought process

**Feature:** `GET /classes/{class_id}/summary`
**Date:** 2026-10-12
**Companion:** `class-summary-plan.md` (the step-by-step implementation plan; it refers to
the decision IDs below). IDs starting with **D** refer to `class-results-decisions.md`.

This document records what was decided, which alternatives were weighed, and why. It is
the raw material for the class summary parts of `NOTES.md`, and for the live-session
walkthrough.

**About the voice:** section 2 is drafted in *your* voice ("I" is you, "Claude" is the AI
assistant), so it can feed NOTES.md directly. Edit it freely. Text in **[brackets]** marks
a reason only you can give; it was left blank rather than invented.

**Current state, in one line:** built and verified in Docker on 2026-10-12, one commit per
phase (`b1c0dc1` to `33828ec`). The design is a triage endpoint backed by a pure module
that reuses the class-results logic, with two bulk queries and 13 lean tests. Every Verify
step in the plan matched; section 4 has the results.

---

## 1. The problem as understood

**The ask, in my words.** The class results endpoint "is great, but it is overwhelming."
As a teacher opening my class, I want to see the most relevant information quickly, at
`GET /classes/{class_id}/summary`.

**My starting sketch:**
- **Struggling students first.** Those who haven't submitted an assignment or a section,
  and which one. Those who are failing, with the assignment and section.
- **Averages per assignment.**
- **An open question:** what else belongs there, without it becoming overwhelming?

**The starting point.** `GET /classes/{class_id}/assessments/{assessment_id}/results`
covers one assessment at a time. It lists every student on the roster with a full
submission, plus a per-section summary. To find what needs action in Room 12A, a teacher
calls it once per assessment and reads 10 student entries to find the 4 students who need
follow-up.

**The core insight.** A summary is a triage list organized by what the teacher will do,
not by how the data is stored. Every item answers one of three questions and points to an
action:

| Question | Action | Response field |
|---|---|---|
| Who needs me, and for what? | Reteach a student; chase a student | `failed`, `not_submitted` |
| What did the whole class not get? | Reteach the whole class | `sections_to_reteach` |
| How is each assessment going? | A quick health check | `assessments` |

Everything else stays one click deeper, in the results endpoint. Every entry carries ids,
so a client can link straight there.

**What the seed data shows:**

| Case in the seed | Why it matters |
|---|---|
| Room 12A's Reading average is 85.8%, but only 2 of 4 submitters passed | Passing needs 80% overall *and* in every section, so an average can clear the bar while half the class fails. Averages need passed counts beside them |
| Room 12A's Math average is 100%, from 1 of 5 students | Averages need submitted counts beside them |
| Room 12B Reading Vocabulary: 0 of 3 passed, 33% average | One lesson to reteach to the whole class, not three individual problems |
| Room 12C Reading Vocabulary: exactly 2 of 4 passed | A boundary case for any "most of the class" rule |
| Room 12C Math: only Taylor (1 of 4) has submitted, and failed | One submission must not trigger whole-class reteaching |
| Jamie Lee failed at 85% (Comprehension 3/4); Riley Johnson failed at 15% | Failures differ hugely in severity, so percentages and points must be visible |
| Nobody in Room 12B has taken Math | If every assessment counts, all 5 students are listed as not having submitted it |
| Alex, Sam, Casey and Riley are each in two classes | Their entries appear in both teachers' summaries, because submissions aren't tied to a class |

---

## 2. How the design evolved (draft, in your voice)

**Step 1: I framed it as a teacher and sketched a structure.** I asked Claude to refine my
sketch in a design session, thinking as a teacher in charge of a classroom, with no
changes to the repo.

**Step 2: Claude read the code before refining anything.** It read the routes, the models,
`class_results.py`, the seed data and `class-results-decisions.md`. That turned up three
constraints my sketch didn't account for:

- **A submission is all or nothing.** `calculate_score` scores every section and counts a
  blank answer as wrong, so "hasn't submitted a section" can't happen: a skipped section
  is stored as 0% and failed. Answers aren't stored, so a skipped section can't be told
  apart from an all-wrong one either.
- **There's no record of which assessments a class was given.** "Not submitted" can't tell
  overdue from never assigned.
- **There are no timestamps and no stored answers.** "Improving or slipping", "new since I
  last looked" and "which questions most students missed" are out of reach.

**Step 3: what was kept, changed and added.**

- **Kept:** separate lists for students who haven't submitted and students who failed.
  Claude agreed with this instinct: chasing a student and teaching a student are
  different actions (S3).
- **Changed:**
  1. "Not submitted" is tracked per assessment only. Sections matter only for failures
     (S4).
  2. A failure lists only the failed sections, with percentages and points, so severity
     is visible: Jamie is one question short, while Riley needs real help (S4).
  3. Failures come first, because "not submitted" is the least certain signal (S3).
  4. Every average sits next to its submitted and passed counts (S16).
  5. Students with nothing to follow up are counted, not listed (S7).
  6. There's no single average across all assessments, because averaging Reading with
     Math tells a teacher nothing (S15).
- **Added:** `sections_to_reteach`, a class-wide view. This was the biggest addition: a
  list of failing students hides the fact that most of the class missed the same skill
  (S6).

**Step 4: the decisions I made.** For each open question, Claude laid out the options with
trade-offs and a recommendation, and I chose:

- **Which assessments count:** every assessment in the catalog (S2), over inferring it
  from submissions or adding an assignments table. **[Your reason; for example, it is the
  simplest option, and it fails loudly rather than silently.]**
- **The reteach rule:** fewer than half the submitters passed, judged only once at least
  half the roster has submitted (S6). **[Your reason.]**
- **Data access:** a fixed number of queries per request, with a refactor phase first, so
  the "only roster students count" rule keeps one home (S9). **[Your reason.]**
- **The plan's format:** executable step by step with exact code, and saved to `docs/`
  like the class-results plan. **[Your reason.]**

**Step 5: verifying the plan without running it.** The plan was written in plan mode,
where nothing can be written to the repo or a scratch copy, and pydantic and FastAPI are
only installed inside Docker. Claude verified the plan in memory instead (S23):

- Every Find block, applied to the real source text, matched exactly once.
- The resulting code ran against the seed in an in-memory database, using small stand-ins
  for pydantic and FastAPI. All 13 new tests passed.
- The expected outputs in the plan's Verify steps matched.

**Mutation testing caught a weak test.** Claude injected six deliberate bugs. One of them
passed every test: sorting `failed` by each student's *highest* failing score instead of
the lowest. No student in the test data had failed two assessments with scores that would
change the order. Claude changed Riley's Math result in the unit test data to a near miss
(83.3% overall, failing only Word Problems at 2/3), and that bug is now caught. All six
are caught (S20).

**Step 6: documents before code.** I asked for this decision log alongside the plan, and
for the session to end with both documents in `docs/` and no code written yet.

**Step 7: running the plan.** Before starting, I asked Claude to explain Phase 1 in depth:
what it does, why it is needed, and why it was built that way. Claude then ran the plan
phase by phase in Docker, and I reviewed and committed each phase before the next. Every
Verify step matched on the first run. Claude added a few checks the plan didn't ask for,
such as real pydantic serialization of a fully nested response and the route's `/docs`
description. It also flagged two places where the plan claimed more than the code
delivers (S9 and S18). Finally, Claude drafted the class summary parts of `NOTES.md` from
this log, for me to edit.

---

## 3. Decision log

### API shape

**S1. A new endpoint: `GET /classes/{class_id}/summary`.**

- **Options:**
  - add results to `GET /classes/{class_id}`
  - `GET /classes/{class_id}/results`, returning one results block per assessment (the
    extension that section 6 of `class-results-decisions.md` anticipated)
  - `GET /classes/{class_id}/summary`
- **Why:**
  - The roster endpoint is ruled out by the provided test that keeps scores out of it.
  - A list of results blocks repeats the overwhelming per-student detail once per
    assessment, the opposite of the ask.
  - The summary is a different resource: a derived view of the class, identified by the
    class id alone. One URL has one response shape, and the roster and results endpoints
    are untouched.
- **How it squares with earlier decisions:**
  - D2 renamed my first "summary" proposal to "results", because per-student results were
    the main content. Here the content really is a summary, so the name fits.
  - D3 (one assessment per request) exists because sections differ between assessments.
    This view never merges sections across assessments: each flagged section stays inside
    its assessment, and every average is per assessment.

**S2. Every assessment in the catalog counts for every class.**

| Option | Verdict | Reason |
|---|---|---|
| **(A) Every assessment in the catalog** | **Chosen** | The simplest option, with no schema change. It fails loudly: extra `not_submitted` entries, explained by a "0 of 5 submitted" row |
| (B) Only assessments at least one roster student has submitted | Rejected | Fails silently: a newly assigned assessment that nobody has started disappears, and one stray submission pulls an assessment in |
| (C) A `class_assessments` table with due dates | Deferred | The correct model, and it would make "missing" and "overdue" honest words. It needs a schema change, seed data and a way to assign, which is beyond this feature |

- **Consequences:**
  - In Room 12A, 4 of 5 students are listed under `not_submitted`, three of them only for
    Math, which only Maya has taken.
  - Room 12B lists all 5 students for Math.
  - The noise grows with the catalog: a Grade 3 class would see Grade 5 tests.
- **[Your reason.]**

**S14. 404 semantics and empty cases.**

- An unknown class gives `404 "Class not found"`, the existing message (D14). There is no
  assessment in the path, so there is no assessment 404.
- A class with no submissions gives **200**, with every student under `not_submitted` for
  every assessment and `null` averages (D9).
- An empty catalog gives **200** with empty lists, and `passed_all_count` equal to the
  roster size (S7).
- An empty roster gives **200** with empty lists, and nothing flagged. This case is not
  tested.

**S5. Ordering.**

- **`failed`:** by each student's lowest failing overall percentage, so the student
  furthest from passing comes first. A student's worst failure decides how urgent they
  are. In the unit test data, Riley (15% on Reading) comes before Casey (71.7%), even
  though Riley's other failure is a near miss at 83.3%.
- **`not_submitted`:** most assessments not submitted first.
- **Ties keep roster order.** Python's `sorted()` is *stable* (equal items keep their input
  order), even with `reverse=True`, and the roster arrives in id order (D15).
- **`sections_to_reteach` and `assessments`:** catalog order, by id. Sorting the reteach
  list worst first was considered. Catalog order keeps sections grouped under their
  assessment, and the list is short.

### Response shape

**S3. Two action lists, not one list per student.**

| Option | Verdict | Reason |
|---|---|---|
| One list per student, with all their issues | Rejected | Forces a ranking between "hasn't submitted Math" and "33% in Vocabulary", which have no common scale |
| **Two lists: `failed` and `not_submitted`** | **Chosen** | Each is a to-do list for one action, with a natural order of its own |
| A `?status=` filter on the results endpoint | Rejected | Still one assessment per call, and still full submissions |

- A student can appear on both lists: Priya failed Reading and hasn't submitted Math.
- `failed` comes first because it is the most certain signal. `not_submitted` is the least
  certain (S2).
- The keys reuse the `ResultStatus` values. "Not submitted" is kept over "missing" (D4).

**S4. A failure lists only the failed sections, reusing `SectionScoreResponse`.**

- Passing sections are noise in a triage view.
- Reusing `SectionScoreResponse` (in the spirit of D6) brings the points along, and they
  show how far off a student is. Jamie's Comprehension is 3/4, one question short; Riley's
  Vocabulary is 0/3.
- **Cost:** each listed section's `passed` field is always `false`. That's redundant, but
  harmless.
- **Edge case:** if an assessment's section weights don't sum to 1, a student can fail on
  the overall score alone, with every section passing. `failed_sections` is then empty.
  This is documented but not tested.

**S7. Students with nothing to follow up are counted, not listed.**

- `passed_all_count` is the roster size minus everyone on either list.
- With no assessments at all, every student counts. That is true, if meaningless, and the
  degenerate-data unit test pins it.

**S15. What is deliberately left out.**

| Left out | Why |
|---|---|
| One average across all assessments | Averaging Reading with Math tells a teacher nothing |
| Points, weights and passing sections for students who passed; submission ids | The results endpoint has them, one click deeper |
| Top performers, for extension work | Useful later, but it doesn't answer "who needs me?" |
| `failed_count` and `not_submitted_count` per assessment | Derivable from `total_students` and the submitted and passed counts |

**S16. Reused models, small models, and reading order.**

- **Reuse (DRY, Don't Repeat Yourself):**
  - `failed_sections` holds `SectionScoreResponse`.
  - `not_submitted` entries hold `AssessmentSummary`.
  - `SectionToReteach` nests `AssessmentSummary` and `SectionResultSummary`.
- **Nesting over the alternatives for `SectionToReteach`:**
  - Copying the fields flat would duplicate six definitions.
  - Subclassing `SectionResultSummary` would leave an ambiguous `id` and put the
    assessment last.
- **Small models.** Each list has its own small model, rather than one large model full
  of optional fields. That is interface segregation applied to data.
- **Field order is reading order.** Pydantic serializes fields in declaration order, so
  raw JSON shows the triage lists before the headline numbers.
- **Every average sits beside its denominators.** Each average has `submitted_count`
  next to it, and each assessment row also has `passed_count`.
- **Earlier conventions hold:** floats are unrounded (D18), and an average of nothing is
  `null` (D9).

**S11. Names.**

- `ClassSummaryResponse`: its docstring notes it is unrelated to the existing
  `ClassSummary`, the id-and-name entry in `GET /classes`.
- `passed_all_count` states a fact, in the spirit of D4.
- The route function is `get_class_summary`, which shadows no import (D28).
- The local variable is `class_` (D27).

### Summary semantics

**S6. The reteach rule.**

| Rule | Flags in the seed | Verdict |
|---|---|---|
| **Fewer than half the submitters passed, once at least half the roster has submitted** | 12B Vocabulary and Comprehension; 12C Comprehension | **Chosen** |
| Section average below `MASTERY_THRESHOLD` (80%), with the same minimum | 12B both; 12C both | Rejected: it recalculates against today's threshold (D5), and an average hides how many students passed |
| Fewer than half passed, with no minimum | Also 12C Computation and Word Problems, from Taylor's single submission | Rejected: one submission would trigger whole-class reteaching |
| Leave it out for now | Nothing | Rejected: the class-wide view is the biggest gain over the results endpoint |

- **Boundaries:**
  - Exactly half passing is **not** flagged (12C Vocabulary, 2 of 4): half the class did
    get it.
  - Exactly half the roster submitting **is** enough to judge.
  - Tests pin both.
- **Implementation:** the comparisons multiply the share instead of dividing to get a
  rate, so there is no division by zero when nobody has submitted or the roster is empty.
  Half of a whole number is exact in floating point, so "exactly half" always lands on
  the boundary.
- **Where the shares live:** `RETEACH_PASS_SHARE` and `RETEACH_MIN_SUBMITTED_SHARE` are
  constants in `src/class_summary.py`, the only module that uses them. The provided
  `src/config.py` is left alone. If a second module needs them, they move there.
- **[Your reason.]**

**S8. The numbers come from `src/class_results.py`.**

- For each assessment, the module calls `build_student_results` and
  `summarize_class_results`.
- Every count and average therefore means exactly what it means on the results endpoint:
  - stored verdicts are read, not recalculated (D5);
  - averages skip students who haven't submitted (D7), average the students' percentages
    (D8), and are `null` when nobody has submitted (D9);
  - sections come from the assessment definition (D10).
- This is the "show all assessments for a class" extension that section 6 of
  `class-results-decisions.md` anticipated, put to work behind a leaner shape.

**S10. `class_summary.py` reads each submission directly.**

- A missing submission means not submitted, and a stored `passed` of false means failed.
  These are the same two facts `StudentResult.status` reads.
- **Why not use `status`?** After checking for a failed status, the `submission` field
  would still be typed `Optional`, even though a failed status always has one. The code
  would then need either an unreachable `None` branch or a type hint that lies.
- **Trade-off:** if a new status is added later, such as `excused`, this module needs a
  matching change.

### Code structure

**S17. Layering: a pure module, with a thin route.**

| Layer | Owns |
|---|---|
| `src/database.py` | SQL only: a shared constant for a class's submissions, plus two bulk read functions |
| `src/class_summary.py` (new) | Pure functions: roster + every assessment + submissions → the summary |
| `src/models.py` | Response shapes |
| `src/app.py` | The route: the 404, fetching the data, one call to the module |

- **Unlike `class_results.py`, this module returns the whole response.** The
  per-assessment loop is logic, not input or output, so it belongs in the pure module.
  The route stays at fetch, 404 and one call.
- The module can be unit-tested with hand-built objects and no database (D12).

**S9. A fixed number of database round trips.**

| Option | Connections per request | Verdict |
|---|---|---|
| Loop the existing per-assessment lookups | 2 + 2N, for N assessments | Rejected: the N+1 query pattern (one query to list N items, then one more per item) makes the cost grow with the catalog, which S2 makes large |
| **Two bulk functions, sharing the submissions SQL** | 3, whatever the catalog size | **Chosen** |

- **Refactor first.** A behavior-neutral phase moves the roster-JOIN SQL into
  `_CLASS_SUBMISSIONS_SQL`, which both submission queries use. The "only roster students
  count" rule and the `ORDER BY rowid` caveat (D16) then live in one place. A check
  confirms the rebuilt SQL is character-for-character identical.
- **Accepted trade-offs:**
  - Each query appends `" ORDER BY sub.rowid"` by convention; the constant's comment says
    so.
  - The one-line `SectionSummary` row mapping now appears in two functions, which isn't
    worth a helper.
  - `get_all_assessment_details` groups sections by assessment in Python, rather than
    querying once per assessment.
- **What the shared SQL really protects** (noted during execution). The roster JOIN is
  only an efficiency filter (S20, D13), so drift in the JOIN alone wouldn't change any
  response. The stronger reason to share the SQL is its column list: both queries feed
  `_row_to_submission`, which reads columns by name, so a column added to one copy and
  not the other would fail at runtime. The `ORDER BY rowid` explanation also keeps one
  home.
- **[Your reason.]**

**S18. Each assessment is computed once.**

- A private, frozen dataclass, `_AssessmentResults`, holds each assessment with its
  submissions and its class summary. Every list builder reads it, instead of recomputing.
- `frozen=True` stops a helper from reassigning an attribute, such as replacing
  `submissions` with another dict. It is shallow, though: the dict and the pydantic models
  inside it can still be changed in place. No helper changes them, so `frozen` guards
  against accidents rather than guaranteeing read-only data. (Corrected during execution;
  the first draft said the data was read-only.)
- It is private because it is only a hand-off between helpers, not part of any interface.

**S19. Code standards.**

- New code gets Google-style docstrings and full type hints. Existing code isn't
  retrofitted (D24).
- The route's docstring ends its public part with `\f` (D30).
- Comments name students rather than using gendered pronouns.

### Testing

**S12. A lean suite in the existing tests' style** (D19). Two new files, with 13 tests:

| File | Tests | What it tests |
|---|---|---|
| `tests/test_class_summary.py` | 7 | `summarize_class` and `needs_reteach`, with hand-built objects and no database |
| `tests/test_class_summary_api.py` | 6 | The route against the seed data, including one submit-then-read end-to-end test |

- **The unit test data** is modeled on Room 12C, plus Morgan, who has submitted nothing.
  It has three deliberate twists:
  - Taylor passes Math, so one student has nothing to follow up.
  - Riley fails Math narrowly, so Riley has failed two assessments with very different
    scores.
  - A failing submission from a student who isn't on the roster must be ignored
    everywhere.
- **Degenerate cases covered:** an empty catalog (unit) and an assessment nobody has
  taken (API, Room 12B Math).

**S20. What the tests pin, and what they deliberately don't.** Six bugs were deliberately
injected to check which decisions the tests protect:

| Bug injected | Decision | Caught? |
|---|---|---|
| Sort `failed` by the highest failing score instead of the lowest | S5 | **Yes,** after the unit data was strengthened (section 2, step 5) |
| Flag a section at exactly half passing (`<=` instead of `<`) | S6 | **Yes:** the unit and API reteach tests |
| Stop judging at exactly half the roster submitting (`>` instead of `>=`) | S6 | **Yes:** `test_needs_reteach_judges_only_once_half_the_roster_has_submitted` |
| Drop the minimum-submissions rule | S6 | **Yes:** that test and the API reteach test |
| List `not_submitted` in roster order instead of most first | S5 | **Yes:** the unit and API not-submitted tests |
| List passing sections as well as failed ones | S4 | **Yes:** three tests |

**Not pinned (lean suite):**
- ties in the `failed` order;
- a failure with no failed section (S4);
- a stored submission missing a section;
- an empty roster;
- an assessment with no sections;
- the JSON field order.

The roster JOIN in the bulk submissions query is not pinned either. It is only an
efficiency filter: the module walks the roster anyway, so a broken JOIN wouldn't change
any response. That's the same reasoning as D13.

**S21. The stale test stays failing** (D23). Every run shows `1 failed`.

### Documentation and scope

**S13. Authorization stays out of scope** (D26). As with the results endpoint, anyone can
read any class. A production version must check that the caller teaches the class.

**S22. Documentation.**

- The endpoint gets a short entry in `python/README.md`, the API reference reviewers read
  (D29).
- The plan and this log live in `docs/`, beside their class-results counterparts.
- `NOTES.md` is mine. At my request, Claude drafted its class summary parts from this
  log, for me to edit.

**S23. Verification before and during execution.** The plan was written in plan mode, so
it couldn't be applied to a scratch copy and run in Docker. Claude verified it in memory
instead, and left real pydantic validation, FastAPI serialization and flake8 to the plan's
Verify steps, with any mismatch stopping execution. When the plan was executed, every
Verify step matched, as section 4 records.

---

## 4. Verification summary

**Before execution,** in memory:

| Check | Result |
|---|---|
| Expected values, computed independently from the seed | Match every expected value in the plan (its Appendix A) |
| The plan's Find blocks, applied in memory to the real source | Each matched exactly once |
| The resulting code, run in memory against the seed (with stand-ins for pydantic and FastAPI) | 13 of 13 new tests pass; the Phase 1, 2 and 4 Verify outputs match |
| The Phase 1 refactor | The rebuilt SQL is character-for-character identical |
| Line length and imports | No new line over 92 characters; no unused imports; the 3 pre-existing E501 (line too long) errors unchanged |
| Mutation testing | 6 of 6 injected bugs caught, after one fix to the unit test data |

**During execution,** in Docker on 2026-10-12. Each phase was committed only after its
checks passed.

| Phase | Check | Result |
|---|---|---|
| 0 | Baseline tests | `1 failed, 31 passed`; only the stale test fails |
| 1 | Rebuilt SQL against the old SQL, then the tests | `sql-unchanged`; `1 failed, 31 passed` |
| 2 | Bulk queries against a fresh seed, then the tests | All three expected lines; tests unchanged |
| 3 | `ClassSummaryResponse` field order, then the tests | As planned; tests unchanged |
| 4 | Room 12C through the real queries and the module, then the tests | Both expected lines; tests unchanged |
| 5 | The new unit tests | `1 failed, 38 passed` |
| 6 | The route in process, for Room 12B and an unknown class | `200 ['student-007', 'student-006', 'student-004'] 404`; `1 failed, 38 passed` |
| 7 | The new API tests | `1 failed, 44 passed` |
| 8 | flake8 | The new and changed files are clean; `database.py` shows only its 3 pre-existing E501 errors |
| 8 | Smoke test against a running server | Skipped: the API container was already running, so it was left alone |
| 10 | Final run | `1 failed, 44 passed`; only the stale test fails |

Checks added beyond the plan:
- A fully nested `ClassSummaryResponse` validated and serialized with real pydantic. Fields
  came out in declaration order, and an empty average serialized as `null`.
- The route's OpenAPI description (what `/docs` shows) stops at `\f`, and its 200 response
  points to the `ClassSummaryResponse` schema.
- Every changed file kept its line endings, and no new line is over 92 characters.

**Not re-run in Docker:** the six injected bugs above. They were checked in memory only,
with stand-ins for pydantic and FastAPI.

---

## 5. Known limitations and what I'd do next

- **No assignments table (S2).** "Not submitted" includes assessments a class was never
  given, and the noise grows with the catalog. A `class_assessments` table with due dates
  would fix this and allow "overdue". The pure module wouldn't change: the route would
  pass it only the class's assessments.
- **Students in two classes** appear in both teachers' summaries, because a submission
  belongs to a student, not a class. This is probably right, since both teachers teach
  those students, but it is worth knowing.
- **No history or timestamps,** so there's no "improving or slipping" and no "new since I
  last looked".
- **No stored answers,** so there's no "everyone missed question 6", which would be the
  sharpest reteaching signal.
- **The reteach rule is a heuristic.** In a class of four, one student changes the
  verdict. The shares are constants; tuning them per class or per teacher would need
  configuration.
- **Authorization** (S13).
- **Duplicate submissions** (D16) affect this view exactly as they affect the results
  endpoint. The UNIQUE index fix applies to both.
- **At scale,** an index on `submissions(student_id)` would help the roster join.

---

## 6. How the design accommodates likely extensions

| Likely ask | How it fits |
|---|---|
| "Only count assessments assigned to the class" | Add a `class_assessments` table and pass only those assessments to `summarize_class`; the module is unchanged |
| "Let teachers tune the reteach rule" | Move the two shares to `config.py`, or accept them as query parameters passed into `needs_reteach` |
| "Show top performers" | One more list builder beside `_failed_students`, reading the same `_AssessmentResults` |
| "Add an `excused` status" | A branch in `StudentResult.status`, and a matching check in `class_summary.py` (S10) |
| "Overdue versus not yet due" | Needs due dates (S2, option C) |
| "Trends over time" | Needs submission history (section 5) |

---

## 7. Mapping to NOTES.md

- **What I built:** S1–S4, S6 and S8, with the reasoning from section 2.
- **Tradeoffs and what I'd do next:** S2, S9, S10 and S20, plus section 5. S2's options
  table is a good "chose the simple option knowingly" story.
- **Working with AI:** section 2 is the collaboration history:
  - my sketch, and how reading the code first reshaped it
  - the four decisions I made from Claude's options
  - what verification caught: a test that couldn't see a wrong sort order
  - Fill in the **[bracketed]** reasons before using it.
- **Status:** Claude has drafted these parts of `NOTES.md` from this log: a "Class summary
  feature" section, five tradeoff bullets, two "with more time" items and a "Class
  summary" paragraph under "Working with AI". Where this log has a **[bracketed]** reason,
  the draft uses the trade-off reasoning recorded here instead, so check it against my
  own reasons.
