from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import settings
from .models import Registry, RegistryEntry


def ensure_storage() -> None:
    settings.raw_scorm_dir.mkdir(parents=True, exist_ok=True)
    settings.courses_dir.mkdir(parents=True, exist_ok=True)
    settings.master_dir.mkdir(parents=True, exist_ok=True)
    if not settings.registry_file.exists():
        settings.registry_file.write_text(json.dumps({"courses": {}}, indent=2), encoding="utf-8")


def load_registry() -> Registry:
    ensure_storage()
    data = json.loads(settings.registry_file.read_text(encoding="utf-8"))
    return Registry.model_validate(data)


def save_registry(registry: Registry) -> None:
    settings.registry_file.write_text(
        json.dumps(registry.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def next_version(course_id: str) -> str:
    registry = load_registry()
    entry = registry.courses.get(course_id)
    if entry is None:
        return "v1"
    latest_num = int(entry.currentVersion.lstrip("v"))
    return f"v{latest_num + 1}"


def update_registry(course_id: str, version: str) -> None:
    registry = load_registry()
    entry = registry.courses.get(course_id)
    if entry is None:
        registry.courses[course_id] = RegistryEntry(currentVersion=version, versions=[version])
    else:
        entry.currentVersion = version
        if version not in entry.versions:
            entry.versions.append(version)
    save_registry(registry)


def course_version_path(course_id: str, version: str) -> Path:
    course_dir = settings.courses_dir / course_id
    course_dir.mkdir(parents=True, exist_ok=True)
    return course_dir / f"{course_id}_{version}.json"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_course_json(course_id: str) -> dict[str, Any] | None:
    registry = load_registry()
    entry = registry.courses.get(course_id)
    if not entry:
        return None
    path = course_version_path(course_id, entry.currentVersion)
    if not path.exists():
        return None
    return read_json(path)
