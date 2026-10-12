# Notes

As I approached this problem, I explored the repo using a combination of looking at the
the code itself and asking Claude questions about it.
I explored the DB using DBeaver as my DB UI.

## How the service works

> *Describe the end-to-end flow in your own words: what happens from HTTP request to stored
> result*

This is a FastAPI app over one SQLite file, assessments.db.
`app.py` holds the routes (validation, 404s),
`database.py` all SQL,
`scoring.py` the pure scoring function, and
`models.py` stores the Pydantic request and response shapes that is used by business logic and the DB
classes (scoring.py and the classes I later created)
On startup, `seed.sql` runs idempotently to make sure the DB is set up.

When an http request, like a POST request is made through (`POST /assessments/{assessment_id}/submit`), it is routed through app.py.
In this case, the submit() function in line 47 in app.py is called.
In the submit() function, a call is made to the DB to get the assessment details from the assessment table in the DB (raises exceptions if not found), including the assessment's sections and answer key.
From there, it calls calculate_score (the function to be implemented in scoring.py), sends it
the submission data and the sections data retrieved from the DB. Once the score is calculated
and returned, and the shape of each score in result["section_scores"] is validated, another call
is made to the DB, via the save_submission() function, to store that submission in the submissions table.
If the submission for a that student_id AND assessment_id already exists, it will UPDATE and overwrite. Else it will create a new row

This is the most involved HTTP requests. ALl the other ones are GETs, which just open a connection to the DB and fetch a piece of data

## Scoring function

> *How did you approach implementing calculate_score? Any edge cases that gave you pause?*

I treated the docstring and `tests/test_scoring.py` as the spec/requirements. As I approached this problem, the first
decision I made was to make sure I wasn't going to touch the tests or change any "legacy" code in app.py.

At its core, the score is essentially being calculated in two nested loops.
For each section in the assessment, calculate_score calls score_section.
In score_section, it loops through each question, and checks the submitted answer against the answer key that was passed in to the function. It then calculates the percentage correct, checks to see if it met the passing threshold for the section then returns all this information in the form of a custom TypedDict, SectionScore.

An edge case that immediately came to mind as I worked on this was answers with errant leading or trailing spaces. I was thinking about it from the point of the students or the teachers. I thought, about what were some of the most fraustrating issues with auto graders during my time as a student and a teaching assistant?
Here are some other edge cases that AI helped me come up with and handle:

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

  Given that parameters of this problem was already pretty well defined, AI was able to accurately and adequately handle most of it by itself. I ensured that the code created followed SOLID design principles (hence all the small helper functions). I also had AI generate the TypedDicts, because I have a personal preference to strongly typed variables whenever I can, because I believe they are easier to debug and maintain.

## Class results feature

> *What did you build? Why did you structure it the way you did? If you chose to extend an
> existing endpoint vs. create a new one, explain that choice.*

This was really interesting. I had fun while thinking through this.
While I was working on this, the main focus was to think about how this would serve the end users (teachers).
I decided to build a new endpoint instead of altering the existing one, because I wanted to preserve "legacy expectations". If users were already using this endpoint to retrieve their class roster, I didn't feel that breaking that expectation gives me any extra benefit. It made much more sense to add a new endpoint for the new functionalities being built.

The other thing that I added here was that there were no unit tests for this section. I feel uncomfortable with submitting untested code, especially since in today's day and age, it so easy to have AI generate tests. I had Claude mirror the structure and style of the unit tests already built in this project for the class-results. They don't test for every single edge case (similar to the original tests), but they test the base functionalities and give me some peace of mind as I move forward. It also helps ensure I don't break any existing functionalities when/if I add more features.

**Built:** `GET /classes/{class_id}/assessments/{assessment_id}/results`. The assessment is
in the path because sections differ between assessments, so a class summary only makes
sense for one; each id also gets a clean 404.

It returns every roster student with a `status` (`passed`, `failed`, `not_submitted`) and
their `submission` (reusing the existing `SubmissionResponse`) or `null`, plus a `summary`:
status counts, the average overall percentage, and per-section submitted and passed counts
and averages. Room 12A on Grade 3 Reading: 4 of 5 submitted, 2 passed, 85.8% average.

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

After this feature was completed, I looked at the result, and I felt that if I was a teacher looking at this, this would not be helpful to me. It is too overwhelming. There is too much going on. Which is why I built this next feature:

## Class summary feature

If I was a teacher using this service, I would (ideally) log in, go to one endpoint, and get all the things that are pertinent to me at a glance. These are the things that I had decided I would want/need, in order:

1. **Who needs me, and for what?** `failed` (reteach a student) and `not_submitted`
   (chase a student), each worst first.
2. **What did the whole class not get?** `sections_to_reteach`.
3. **How is each assessment going?** `assessments`: submitted, passed, average.

**Built:** `GET /classes/{class_id}/summary`, an at-a-glance triage view of one class
across every assessment. The results endpoint is complete but overwhelming: to find who
needs follow-up in Room 12A, a teacher calls it once per assessment and reads 10 student
entries to find the 4 who need something. The summary is organized by what the teacher
will do next instead:

- **`failed`** (reteach a student): who failed which assessment, with only the failed
  sections and their points, furthest from passing first.
- **`not_submitted`** (chase a student): who hasn't submitted which assessment, most
  missing first.
- **`sections_to_reteach`** (reteach the whole class): sections most of the class didn't
  pass.
- **`assessments`** (a health check): submitted and passed counts and the average for each
  assessment.

Students with nothing to follow up are counted in `passed_all_count`, not listed. Room 12A
returns Priya (70%, Comprehension 2/4) and Alex (73.3%, Vocabulary 1/3) as failed; Sam
(Reading and Math) and Jordan, Priya and Alex (Math) as not submitted; nothing to reteach;
and a `passed_all_count` of 1 (Maya). Every entry carries ids, so a client can link to the
full results.

Rules that shaped it:

- **Every assessment counts for every class.** Nothing records which assessments a class
  was given. Of three options (the whole catalog, only assessments someone in the class
  has submitted, or a new assignments table), I chose the catalog: it's the simplest,
  needs no schema change, and fails loudly. Inferring from submissions fails silently,
  since a newly assigned assessment nobody has started would vanish. The cost is noise:
  in Room 12A, Jordan, Priya and Alex are listed for Math, which only Maya has taken.
- **"Not submitted" is per assessment, not per section.** A submission is all or nothing:
  a skipped section is scored 0% and fails, so it shows up under `failed` instead.
- **Failures show severity.** Jamie failed at 85%, one Comprehension question short (3/4);
  Riley scored 15%. Listing only the failed sections, with points, makes that visible, and
  sorting by each student's *lowest* failing score puts the student furthest from passing
  first. Ties keep roster order.
- **The reteach rule:** flag a section when fewer than half of its submitters passed, but
  only once at least half the roster has submitted. Room 12B Vocabulary (0 of 3 passed) is
  flagged; Room 12C Math, where only Taylor has submitted, isn't judged, because one
  submission shouldn't trigger whole-class reteaching. Exactly half passing isn't flagged:
  half the class did get it. I rejected "section average under 80%": it re-judges against
  today's threshold and hides how many students passed.
- **Every average sits beside its counts.** Room 12A's Reading average is 85.8%, yet only
  2 of 4 submitters passed; its Math average of 100% comes from 1 student of 5. There's no
  average across assessments: averaging Reading with Math tells a teacher nothing.
- **Same numbers as the results endpoint.** Each assessment's counts and averages come from
  `class_results.py`, so "submitted", "passed" and "average" mean exactly the same thing.

**Structure** follows the results feature: a thin route (404, fetch, one call) and a new
pure module, `class_summary.py`, that builds the whole response and is unit-tested without
a database. `database.py` gains two bulk queries, so a request makes three database calls
however many assessments exist, instead of two more per assessment. A refactor came first:
the roster-filtered submissions SQL moved into one shared constant, so the old and new
queries can't drift apart. 13 new tests: 7 unit and 6 API, including one that submits and
then reads the summary back.

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
- **The summary counts every assessment for every class:** simple and loud about what it
  doesn't know, but noisy, and the noise grows with the catalog.
- **The reteach rule is a heuristic:** in a class of four, one student flips the verdict.
  Its two shares are constants in `class_summary.py`, the only module that uses them,
  rather than in the provided `config.py`.
- **Bulk queries for the summary:** three database calls whatever the catalog size, rather
  than two more per assessment. The cost: sections are grouped in Python, and each query
  appends its own `ORDER BY` to the shared SQL, a convention only a comment enforces.
- **The summary reads each stored verdict directly** instead of through `status`, which
  avoids an unreachable `None` check, but a new status such as `excused` would need a
  matching change there.
- **The summary's 13 tests are lean too.** Six bugs injected on purpose while checking the
  plan (a wrong sort order in each list, both reteach boundaries, dropping the minimum,
  listing passed sections) are all caught. Ties, an empty roster and a failure with no
  failed section are deliberately untested.

**With more time**

- **Authentication and Authorization:** only the class's teacher should see results/
- **A `UNIQUE (student_id, assessment_id)` index plus an upsert,** since a duplicate row
  could hide a resubmission.
- **Submission history with timestamps and stored answers,** so a resubmission doesn't
  erase the old score (as in the README example) and teachers get trends, allow for comparison across cohorts and question-level insight.
- **An assignments table with due dates,** to tell "not submitted" from "never assigned",
  and "overdue" from "not yet due". It would also cut the summary's noise without changing
  its module: the route would pass in only the class's assessments.
- **Let teachers tune the reteach rule** per class, instead of two fixed constants.
- **Scoring tests** for the case, whitespace and stray-answer rules, and one consistent rule
  for empty sections and empty assessments.
- **Pin dependencies** and retire the stale test.

## Working with AI

> *How did you use AI tools? What did you prompt, what came back, what did you change and
> why? Think of this as a reflection on the collaboration, not a log.*

I used Claude Code as a pair programmer that explains its changes. Before it touches the repo, I have it detail all the changes it plans to make. I review the changes thoroughly. Make sure it makes sense, and then I have it implement it phase by phase.

The detailed plans and decision logs for the project can be found under docs/

Its plans are intentionally broken up into small phases so that I can review each phase before implementation and before commit. For this project, I also made sure to have at most one phase per commit, so that if anything went wrong, it would be easy to revert.

I believe that Claude can program (in many cases) better and faster than many humans, or in the areas that it cannot yet, it will be able to, soon. My job is not to do work that can be done better by a machine, but to reimagine what is needed by the humans in this process and ensure that the machine is aligned with those needs. My job is to understand the '**human**' aspect of our projects and to figure out how I can best leverage all the tools in my toolset, including AI, to better achieve that goal.
