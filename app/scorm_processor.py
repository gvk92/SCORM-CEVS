from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

from .config import settings
from .models import ContentBlock, CourseVersion, Lesson, Module
from .storage import (
    course_version_path,
    latest_course_json,
    next_version,
    update_registry,
    write_json,
)
from .versioning import compute_change_summary


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _strip_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.split())


def _save_raw_zip(source_zip: Path, course_id: str) -> Path:
    target = settings.raw_scorm_dir / f"{course_id}_{_timestamp()}.zip"
    with source_zip.open("rb") as src, target.open("wb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)
    return target


def _safe_member_target(extract_root: Path, member_name: str) -> Path:
    member_path = Path(member_name)
    if member_path.is_absolute():
        member_path = Path(*member_path.parts[1:])
    target = (extract_root / member_path).resolve()
    if not str(target).startswith(str(extract_root.resolve())):
        raise ValueError(f"Unsafe ZIP entry path: {member_name}")
    return target


def _stream_extract_zip(zip_path: Path, extract_to: Path) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            member_target = _safe_member_target(extract_to, info.filename)
            if info.is_dir():
                member_target.mkdir(parents=True, exist_ok=True)
                continue
            member_target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info, "r") as src, member_target.open("wb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)


def _build_resources(root: ET.Element, ns: dict[str, str]) -> dict[str, str]:
    resources: dict[str, str] = {}
    res_nodes = root.findall(".//ns:resource", ns) if ns else root.findall(".//resource")
    for res in res_nodes:
        ident = res.attrib.get("identifier")
        href = res.attrib.get("href", "")
        base = res.attrib.get("{http://www.w3.org/XML/1998/namespace}base", "")
        full_href = f"{base}{href}" if base and href else href
        if ident:
            resources[ident] = full_href
    return resources


def _parse_manifest(manifest_path: Path) -> tuple[str, list[Module]]:
    tree = ET.parse(manifest_path)
    root = tree.getroot()

    ns = {"ns": root.tag.split("}")[0].strip("{")} if "}" in root.tag else {}
    title_node = root.find(".//ns:organization/ns:title", ns) if ns else root.find(".//organization/title")
    course_title = _strip_text(title_node.text if title_node is not None else "Untitled Course")
    resources = _build_resources(root, ns)

    org = root.find(".//ns:organization", ns) if ns else root.find(".//organization")
    if org is None:
        return course_title, []

    modules: list[Module] = []

    def walk_item(item: ET.Element, path_titles: list[str], root_module: Module) -> None:
        title_node = next((n for n in list(item) if n.tag.endswith("title")), None)
        title = _strip_text(title_node.text if title_node is not None else item.attrib.get("identifier", "Untitled"))
        children = [child for child in list(item) if child.tag.endswith("item")]

        new_path = path_titles + [title]
        identifierref = item.attrib.get("identifierref")

        if identifierref and not children:
            lesson_id = item.attrib.get("identifier", title)
            href = resources.get(identifierref, "")
            lesson_title = " > ".join(new_path)
            root_module.lessons.append(Lesson(id=lesson_id, title=lesson_title, href=href))
            return

        for child in children:
            walk_item(child, new_path, root_module)

    for item in [child for child in list(org) if child.tag.endswith("item")]:
        top_title_node = next((n for n in list(item) if n.tag.endswith("title")), None)
        module_title = _strip_text(top_title_node.text if top_title_node is not None else "Untitled Module")
        module_id = item.attrib.get("identifier", module_title)
        module = Module(id=module_id, title=module_title, lessons=[])

        walk_item(item, [], module)

        if not module.lessons:
            identifierref = item.attrib.get("identifierref")
            if identifierref:
                module.lessons.append(
                    Lesson(
                        id=module_id,
                        title=module_title,
                        href=resources.get(identifierref, ""),
                    )
                )
        modules.append(module)

    return course_title, modules


def _extract_block_text(node) -> str:
    return _strip_text(node.get_text(" ", strip=True))


def _is_ui_noise(tag) -> bool:
    cls = " ".join(tag.get("class", [])).lower()
    ident = (tag.get("id") or "").lower()
    noise_patterns = [
        "nav", "menu", "breadcrumb", "footer", "header", "sidebar", "pagination", "copyright", "btn",
    ]
    return any(p in cls or p in ident for p in noise_patterns)


def _extract_interactives(soup: BeautifulSoup) -> list[ContentBlock]:
    blocks: list[ContentBlock] = []

    mapping = {
        "accordion": ["accordion", "collapse", "expander"],
        "tabs": ["tab", "tabs", "tabpanel"],
        "flipcard": ["flip", "card-front", "card-back"],
        "carousel": ["carousel", "slide"],
        "expandable": ["expand", "drawer", "details"],
    }

    for block_type, keywords in mapping.items():
        for node in soup.find_all(
            lambda tag: tag.name in {"div", "section", "article", "details"}
            and any(k in " ".join(tag.get("class", [])).lower() for k in keywords)
        ):
            if _is_ui_noise(node):
                continue
            title = None
            heading = node.find(["h1", "h2", "h3", "h4", "summary", "button"])
            if heading:
                title = _extract_block_text(heading)

            items = []
            for child in node.find_all(["section", "article", "div", "li"], recursive=True):
                child_text = _extract_block_text(child)
                if len(child_text) < 8:
                    continue
                child_title_node = child.find(["h2", "h3", "h4", "summary", "button", "strong"])
                child_title = _extract_block_text(child_title_node) if child_title_node else None
                items.append({"title": child_title, "text": child_text})

            text = _extract_block_text(node)
            if text:
                blocks.append(ContentBlock(type=block_type, title=title, text=text, items=items[:25]))

    return blocks


def _extract_text_blocks(soup: BeautifulSoup) -> list[ContentBlock]:
    blocks: list[ContentBlock] = []

    for dead in soup(["script", "style", "noscript", "svg", "nav", "footer", "header", "form"]):
        dead.decompose()

    interactives = _extract_interactives(soup)
    blocks.extend(interactives)

    for node in soup.find_all(["p", "li", "div", "span", "h1", "h2", "h3", "h4"]):
        if _is_ui_noise(node):
            continue
        text = _extract_block_text(node)
        if len(text) < 3:
            continue
        blocks.append(ContentBlock(type="text", text=text))

    deduped: list[ContentBlock] = []
    seen: set[tuple[str, str]] = set()
    for block in blocks:
        key = (block.type, block.text or "")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(block)

    return deduped




def _safe_lesson_path(extract_root: Path, href: str) -> Path | None:
    if not href:
        return None
    candidate = (extract_root / href.lstrip('/')).resolve()
    if not str(candidate).startswith(str(extract_root.resolve())):
        return None
    return candidate

def _populate_lesson_content(extract_root: Path, modules: list[Module]) -> list[Module]:
    for module in modules:
        for lesson in module.lessons:
            if not lesson.href:
                continue
            lesson_path = _safe_lesson_path(extract_root, lesson.href)
            if not lesson_path or not lesson_path.exists() or lesson_path.suffix.lower() not in {".htm", ".html", ".xhtml"}:
                continue
            html = lesson_path.read_text(encoding="utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")
            lesson.content_blocks = _extract_text_blocks(soup)
    return modules


def process_scorm_zip(zip_path: Path, course_id: str) -> dict:
    raw_zip_path = _save_raw_zip(zip_path, course_id)
    version = next_version(course_id)

    with tempfile.TemporaryDirectory(prefix="scorm_extract_") as tmp_dir:
        extract_root = Path(tmp_dir)
        _stream_extract_zip(raw_zip_path, extract_root)

        manifest_path = extract_root / "imsmanifest.xml"
        if not manifest_path.exists():
            raise FileNotFoundError("imsmanifest.xml not found in SCORM package")

        course_title, modules = _parse_manifest(manifest_path)
        modules = _populate_lesson_content(extract_root, modules)

    created_at = datetime.now(timezone.utc).isoformat()
    current_data = CourseVersion(
        course_id=course_id,
        version=version,
        created_at=created_at,
        source_file=str(raw_zip_path),
        course_title=course_title,
        modules=modules,
    ).model_dump()

    previous_data = latest_course_json(course_id)
    current_data["change_summary"] = compute_change_summary(previous_data, current_data).model_dump()

    output_path = course_version_path(course_id, version)
    write_json(output_path, current_data)
    update_registry(course_id, version)
    return current_data


def rebuild_master_json() -> dict:
    from .storage import load_registry, read_json, course_version_read_path

    registry = load_registry()
    courses = []

    for course_id, entry in registry.courses.items():
        latest_path = course_version_read_path(course_id, entry.currentVersion)
        if latest_path.exists():
            courses.append(read_json(latest_path))

    master = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "courses": courses,
    }
    settings.master_file.write_text(json.dumps(master, indent=2, ensure_ascii=False), encoding="utf-8")
    return master
