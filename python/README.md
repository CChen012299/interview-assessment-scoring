# Assessment Scoring Service — Python

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Docker Compose

## Getting started

```bash
docker compose up
```

The API will be available at `http://localhost:8000`.

## Running the tests

```bash
docker compose run test
```

Before you implement the scoring function, 8 tests pass and 8 fail. All 16 should pass once your implementation is correct.

One provided test, `test_submit_returns_500_before_scoring_implemented`, checks behavior
from before the scoring function existed and is expected to fail (see
`../NOTES.md`). After changing code, add `--build` so the image picks up your
changes: `docker compose run --rm --build test`.

## API reference

### Submit an assessment

```bash
curl -X POST http://localhost:8000/assessments/assess-001/submit \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "student-001",
    "answers": {
      "q-001": "author",
      "q-002": "setting",
      "q-004": "main idea"
    }
  }'
```

### Get a student's scores

```bash
curl http://localhost:8000/students/student-001/scores
```

### List classes

```bash
curl http://localhost:8000/classes
```

### Get a class with its students

```bash
curl http://localhost:8000/classes/class-001
```

### Get a class's results for an assessment

```bash
curl http://localhost:8000/classes/class-001/assessments/assess-001/results
```

Lists every student on the class roster with a `status` of `passed`, `failed` or
`not_submitted`, and their `submission` (overall percentage and per-section scores), which
is `null` if they have not submitted. A `summary` gives status counts, the average overall
percentage, and, for each section of the assessment, how many students submitted, how many
passed and their average. Averages include only students who submitted and are `null` when
nobody has. Returns 404 if the class or the assessment does not exist.

### Get a class's summary

```bash
curl http://localhost:8000/classes/class-001/summary
```

A short triage view across every assessment. `failed` lists the students who failed an
assessment, furthest from passing first, with only the sections they failed.
`not_submitted` lists the students who have not submitted an assessment, most first.
`sections_to_reteach` flags sections that fewer than half of the submitters passed, once
at least half the class has submitted. `assessments` gives each assessment's submitted
and passed counts and average. Students with nothing to follow up are only counted, in
`passed_all_count`. Every assessment counts for every class, because there is no record
of which assessments a class was given. Returns 404 if the class does not exist.

### List assessments

```bash
curl http://localhost:8000/assessments
```

### Get assessment detail

```bash
curl http://localhost:8000/assessments/assess-001
```

## What to implement

**Part 1 — Scoring function:** Open `src/scoring.py`. The function `calculate_score` is stubbed out — read the docstring carefully, then implement it. The tests in `tests/test_scoring.py` define exactly what it should do.

**Part 2 — Class results feature:** The `GET /classes/{class_id}` endpoint returns a class roster but no assessment data. Extend the API so it also returns each student's latest score for a given assessment. Design the API shape yourself.

## What to submit

Fill in `../NOTES.md.template` and bring it to the live session.
