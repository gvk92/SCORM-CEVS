from __future__ import annotations

from pathlib import Path


class Settings:
    storage_root: Path = Path("storage")
    raw_scorm_dir: Path = storage_root / "raw_scorms"
    courses_dir: Path = storage_root / "courses"
    master_dir: Path = storage_root / "master"
    registry_file: Path = storage_root / "registry.json"
    master_file: Path = master_dir / "master_courses.json"


settings = Settings()
