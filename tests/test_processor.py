from __future__ import annotations

import json
import zipfile
from pathlib import Path

from app.config import settings
from app.scorm_processor import process_scorm_zip, rebuild_master_json
from app.storage import ensure_storage


def _make_scorm(path: Path, lesson_text: str) -> None:
    manifest = """<?xml version='1.0' encoding='UTF-8'?>
<manifest identifier='MANIFEST'>
  <organizations default='ORG'>
    <organization identifier='ORG'>
      <title>Demo Course</title>
      <item identifier='MODULE1'>
        <title>Module 1</title>
        <item identifier='SUB1'>
          <title>Submodule 1</title>
          <item identifier='LESSON1' identifierref='RES1'>
            <title>Lesson One</title>
          </item>
        </item>
      </item>
    </organization>
  </organizations>
  <resources>
    <resource identifier='RES1' href='lesson1.html' type='webcontent'/>
  </resources>
</manifest>
"""
    html = f"""<html><body>
      <div class='accordion'><h3>Details</h3><p>{lesson_text}</p></div>
      <div class='nav'>ignore this nav text</div>
      <p>Body copy.</p>
    </body></html>"""

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("imsmanifest.xml", manifest)
        zf.writestr("lesson1.html", html)


def test_process_and_versioning(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "storage_root", tmp_path / "storage")
    monkeypatch.setattr(settings, "raw_scorm_dir", settings.storage_root / "raw_scorms")
    monkeypatch.setattr(settings, "courses_dir", settings.storage_root / "courses")
    monkeypatch.setattr(settings, "master_dir", settings.storage_root / "master")
    monkeypatch.setattr(settings, "registry_file", settings.storage_root / "registry.json")
    monkeypatch.setattr(settings, "master_file", settings.master_dir / "master_courses.json")

    ensure_storage()

    zip1 = tmp_path / "course.zip"
    _make_scorm(zip1, "Welcome v1")
    v1 = process_scorm_zip(zip1, course_id="course-abc")
    assert v1["version"] == "v1"
    assert v1["change_summary"]["added_lessons"] == ["LESSON1"]
    assert any("Submodule 1" in l["title"] for m in v1["modules"] for l in m["lessons"])
    assert not any("ignore this nav text" in (b.get("text") or "") for m in v1["modules"] for l in m["lessons"] for b in l["content_blocks"])

    v1_path = settings.courses_dir / "course-abc" / "course-abc_v1.json"
    assert v1_path.exists()

    zip2 = tmp_path / "course_v2.zip"
    _make_scorm(zip2, "Welcome v2")
    v2 = process_scorm_zip(zip2, course_id="course-abc")
    assert v2["version"] == "v2"
    assert "LESSON1" in v2["change_summary"]["updated_lessons"]

    master = rebuild_master_json()
    assert len(master["courses"]) == 1
    assert master["courses"][0]["version"] == "v2"

    master_disk = json.loads(settings.master_file.read_text(encoding="utf-8"))
    assert master_disk["courses"][0]["version"] == "v2"


def test_rejects_unsafe_zip_entries(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "storage_root", tmp_path / "storage")
    monkeypatch.setattr(settings, "raw_scorm_dir", settings.storage_root / "raw_scorms")
    monkeypatch.setattr(settings, "courses_dir", settings.storage_root / "courses")
    monkeypatch.setattr(settings, "master_dir", settings.storage_root / "master")
    monkeypatch.setattr(settings, "registry_file", settings.storage_root / "registry.json")
    monkeypatch.setattr(settings, "master_file", settings.master_dir / "master_courses.json")

    ensure_storage()
    bad_zip = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("imsmanifest.xml", "<manifest></manifest>")
        zf.writestr("../escape.txt", "should not extract")

    try:
        process_scorm_zip(bad_zip, course_id="bad-course")
        assert False, "Expected unsafe ZIP path to raise ValueError"
    except ValueError as exc:
        assert "Unsafe ZIP entry path" in str(exc)


def test_manifest_href_path_traversal_is_ignored(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "storage_root", tmp_path / "storage")
    monkeypatch.setattr(settings, "raw_scorm_dir", settings.storage_root / "raw_scorms")
    monkeypatch.setattr(settings, "courses_dir", settings.storage_root / "courses")
    monkeypatch.setattr(settings, "master_dir", settings.storage_root / "master")
    monkeypatch.setattr(settings, "registry_file", settings.storage_root / "registry.json")
    monkeypatch.setattr(settings, "master_file", settings.master_dir / "master_courses.json")

    ensure_storage()

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
    <resource identifier='RES1' href='../outside.html' type='webcontent'/>
  </resources>
</manifest>
"""

    bad_href_zip = tmp_path / "bad_href.zip"
    with zipfile.ZipFile(bad_href_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("imsmanifest.xml", manifest)

    payload = process_scorm_zip(bad_href_zip, course_id="course-safe")
    lesson = payload["modules"][0]["lessons"][0]
    assert lesson["href"] == "../outside.html"
    assert lesson["content_blocks"] == []
