from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


class PyrightEnvsError(Exception):
    pass


@dataclass(frozen=True)
class Package:
    root: str
    source_paths: list[str]
    vendor_paths: list[str]
    test_paths: list[str]


@dataclass
class Diagnostics:
    skipped_no_python: list[str] = field(default_factory=list)


def to_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def dedup(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            result.append(path)
    return result


def existing(root: Path, paths: list[str]) -> list[str]:
    return [path for path in paths if (root / path).exists()]


def has_python(root: Path, paths: list[str]) -> bool:
    for rel in paths:
        base = root / rel
        if base.is_file():
            if base.suffix == ".py":
                return True
            continue
        if base.is_dir() and next(base.rglob("*.py"), None) is not None:
            return True
    return False
