from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

from .scorm_processor import process_scorm_zip, rebuild_master_json
from .storage import ensure_storage, load_registry, latest_course_json

app = FastAPI(title="SCORM Content Extraction and Versioning System")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def startup() -> None:
    ensure_storage()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/courses")
def courses() -> dict:
    registry = load_registry()
    items = []
    for course_id, entry in registry.courses.items():
        latest = latest_course_json(course_id)
        if latest is None:
            continue
        items.append(
            {
                "course_id": course_id,
                "course_title": latest.get("course_title", "Untitled"),
                "current_version": entry.currentVersion,
                "status": entry.status,
                "lesson_count": sum(len(m.get("lessons", [])) for m in latest.get("modules", [])),
                "updated_at": latest.get("created_at"),
            }
        )
    items.sort(key=lambda c: (c["course_title"].lower(), c["course_id"]))
    return {"courses": items}


@app.post("/upload")
async def upload_scorm(course_id: str, file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip SCORM packages are supported")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        while chunk := await file.read(1024 * 1024):
            tmp.write(chunk)
        temp_zip_path = Path(tmp.name)

    try:
        payload = process_scorm_zip(temp_zip_path, course_id=course_id)
        master = rebuild_master_json()
        return {
            "course": payload,
            "master_course_count": len(master["courses"]),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        temp_zip_path.unlink(missing_ok=True)


@app.post("/upload/bulk")
async def upload_bulk(course_ids: str, files: list[UploadFile] = File(...)) -> dict:
    ids = [cid.strip() for cid in course_ids.split(",") if cid.strip()]
    if len(ids) != len(files):
        raise HTTPException(status_code=400, detail="course_ids count must match files count")

    results = []
    for course_id, file in zip(ids, files):
        if not file.filename or not file.filename.lower().endswith(".zip"):
            raise HTTPException(status_code=400, detail=f"File for {course_id} must be a .zip SCORM package")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            while chunk := await file.read(1024 * 1024):
                tmp.write(chunk)
            temp_zip_path = Path(tmp.name)

        try:
            payload = process_scorm_zip(temp_zip_path, course_id=course_id)
            results.append({"course_id": course_id, "version": payload["version"]})
        finally:
            temp_zip_path.unlink(missing_ok=True)

    rebuild_master_json()
    return {"processed": results}
