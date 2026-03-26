# SCORM-CEVS

SCORM Content Extraction and Versioning System (CEVS) that converts SCORM packages into structured, versioned JSON for AI consumption.

## What it does

- Accepts `.zip` SCORM packages (single or bulk).
- Persists raw uploads to disk.
- Streams ZIP extraction to temporary disk folders (no full in-memory unzip).
- Parses `imsmanifest.xml` for course/module/lesson hierarchy, including nested items.
- Extracts text from lesson HTML, including interactive containers (accordion, tabs, flipcards, carousels, expandable sections).
- Filters common UI noise (nav/footer/menu/button-heavy wrappers) from content output.
- Produces versioned per-course JSON (`{courseId}_v1.json`, `{courseId}_v2.json`, ...).
- Maintains a `master_courses.json` containing only latest LIVE course versions.
- Provides a friendly web dashboard at `/` for uploads and live catalog monitoring.

## Storage layout

```text
/storage/
  raw_scorms/
    {courseId}_{timestamp}.zip

  courses/
    {courseId}/
      {courseId}_v1.json
      {courseId}_v2.json

  master/
    master_courses.json

  registry.json
```

## API endpoints

- `GET /` (dashboard UI)
- `GET /health`
- `GET /courses`
- `POST /upload?course_id=<id>`
  - multipart with one file field named `file`
- `POST /upload/bulk?course_ids=id1,id2,...`
  - multipart with multiple `files`

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Install all local dependencies

Run this once on a new machine to install both Node and Python requirements:

If Python 3.14+ is detected, setup automatically uses a flexible dependency set (`requirements-flex.txt`) to avoid pinned packages that may not yet ship wheels for newer interpreters.

```bash
npm run setup
```

## Run with npm

```bash
npm start
```

For hot reload during development:

```bash
npm run start:reload
```

## Test

```bash
npm run test
```


### Windows note

The npm scripts auto-detect `python`, `python3`, or `py`. So Windows (`py`) and Linux/macOS (`python3`) setups both work with `npm run setup` and `npm start`.
