from __future__ import annotations

import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.storage import ensure_storage


def _make_scorm(path: Path) -> None:
    manifest = """<?xml version='1.0' encoding='UTF-8'?>
<manifest identifier='MANIFEST'>
  <organizations default='ORG'>
    <organization identifier='ORG'>
      <title>Demo Course</title>
      <item identifier='MODULE1'>
        <title>Module 1</title>
        <item identifier='LESSON1' identifierref='RES1'>
          <title>Lesson One</title>
        </item>
      </item>
    </organization>
  </organizations>
  <resources>
    <resource identifier='RES1' href='lesson1.html' type='webcontent'/>
  </resources>
</manifest>
"""
    html = "<html><body><p>Hello world</p></body></html>"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("imsmanifest.xml", manifest)
        zf.writestr("lesson1.html", html)


def test_output_endpoints(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "storage_root", tmp_path / "storage")
    monkeypatch.setattr(settings, "raw_scorm_dir", settings.storage_root / "raw_scorms")
    monkeypatch.setattr(settings, "courses_dir", settings.storage_root / "courses")
    monkeypatch.setattr(settings, "master_dir", settings.storage_root / "master")
    monkeypatch.setattr(settings, "registry_file", settings.storage_root / "registry.json")
    monkeypatch.setattr(settings, "master_file", settings.master_dir / "master_courses.json")

    ensure_storage()

    zip_path = tmp_path / "course.zip"
    _make_scorm(zip_path)

    client = TestClient(app)
    with zip_path.open("rb") as f:
        res = client.post("/upload", params={"course_id": "api-course"}, files={"file": ("course.zip", f, "application/zip")})
    assert res.status_code == 200

    latest = client.get("/courses/api-course/latest")
    assert latest.status_code == 200
    assert latest.json()["version"] == "v1"

    latest_dl = client.get("/courses/api-course/latest/download")
    assert latest_dl.status_code == 200
    assert latest_dl.headers["content-type"].startswith("application/json")

    master = client.get("/master")
    assert master.status_code == 200
    assert len(master.json()["courses"]) == 1

    master_dl = client.get("/master/download")
    assert master_dl.status_code == 200
    assert master_dl.headers["content-type"].startswith("application/json")
