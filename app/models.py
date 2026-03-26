from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ContentBlock(BaseModel):
    type: Literal["text", "accordion", "tabs", "flipcard", "carousel", "expandable"]
    title: str | None = None
    text: str | None = None
    items: list[dict] = Field(default_factory=list)


class Lesson(BaseModel):
    id: str
    title: str
    href: str
    content_blocks: list[ContentBlock] = Field(default_factory=list)


class Module(BaseModel):
    id: str
    title: str
    lessons: list[Lesson] = Field(default_factory=list)


class ChangeSummary(BaseModel):
    added_lessons: list[str] = Field(default_factory=list)
    removed_lessons: list[str] = Field(default_factory=list)
    updated_lessons: list[str] = Field(default_factory=list)


class CourseVersion(BaseModel):
    course_id: str
    version: str
    created_at: str
    source_file: str
    course_title: str
    modules: list[Module]
    change_summary: ChangeSummary = Field(default_factory=ChangeSummary)


class RegistryEntry(BaseModel):
    currentVersion: str
    status: Literal["LIVE", "ARCHIVED"] = "LIVE"
    versions: list[str] = Field(default_factory=list)


class Registry(BaseModel):
    courses: dict[str, RegistryEntry] = Field(default_factory=dict)
