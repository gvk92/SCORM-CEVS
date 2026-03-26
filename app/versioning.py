from __future__ import annotations

from collections.abc import Iterable

from .models import ChangeSummary


def _lesson_fingerprints(course_data: dict) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for module in course_data.get("modules", []):
        for lesson in module.get("lessons", []):
            key = lesson.get("id") or lesson.get("href")
            if not key:
                continue
            blocks = lesson.get("content_blocks", [])
            text = "|".join((b.get("type", "") + ":" + (b.get("text") or "")) for b in blocks)
            fingerprints[key] = text
    return fingerprints


def lesson_ids(course_data: dict) -> set[str]:
    ids: set[str] = set()
    for module in course_data.get("modules", []):
        for lesson in module.get("lessons", []):
            lesson_key = lesson.get("id") or lesson.get("href")
            if lesson_key:
                ids.add(lesson_key)
    return ids


def compute_change_summary(previous: dict | None, current: dict) -> ChangeSummary:
    if not previous:
        return ChangeSummary(added_lessons=sorted(lesson_ids(current)))

    prev_ids = lesson_ids(previous)
    curr_ids = lesson_ids(current)
    added = sorted(curr_ids - prev_ids)
    removed = sorted(prev_ids - curr_ids)

    prev_fp = _lesson_fingerprints(previous)
    curr_fp = _lesson_fingerprints(current)

    shared: Iterable[str] = prev_ids.intersection(curr_ids)
    updated = sorted([lesson_id for lesson_id in shared if prev_fp.get(lesson_id) != curr_fp.get(lesson_id)])
    return ChangeSummary(added_lessons=added, removed_lessons=removed, updated_lessons=updated)
