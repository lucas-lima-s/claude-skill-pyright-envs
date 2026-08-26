from __future__ import annotations

from pathlib import Path

from providers import layout
from providers.common import Diagnostics


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def test_discovers_package_with_source_and_vendor(tmp_path: Path) -> None:
    _touch(tmp_path / "packages/one/src/one_app/__init__.py")
    _touch(tmp_path / "packages/one/vendor/sharedlib/__init__.py")

    packages = layout.discover({"packages": "packages/*"}, tmp_path)

    assert len(packages) == 1
    assert packages[0].root == "packages/one"
    assert packages[0].source_paths == ["packages/one/src"]
    assert packages[0].vendor_paths == ["packages/one/vendor"]


def test_extra_paths_order_is_source_then_vendor_then_test(tmp_path: Path) -> None:
    _touch(tmp_path / "packages/one/src/one_app/__init__.py")
    _touch(tmp_path / "packages/one/vendor/sharedlib/__init__.py")
    _touch(tmp_path / "packages/one/tests/test_one.py")

    packages = layout.discover({"packages": "packages/*"}, tmp_path)

    assert packages[0].source_paths == ["packages/one/src"]
    assert packages[0].vendor_paths == ["packages/one/vendor"]
    assert packages[0].test_paths == ["packages/one/tests"]


def test_skip_prefixes_excludes_matching_directories(tmp_path: Path) -> None:
    _touch(tmp_path / "packages/_internal/src/mod/__init__.py")
    _touch(tmp_path / "packages/kept/src/mod/__init__.py")

    packages = layout.discover({"packages": "packages/*", "skip_prefixes": ["_", "."]}, tmp_path)

    roots = [p.root for p in packages]
    assert "packages/kept" in roots
    assert "packages/_internal" not in roots


def test_require_python_filters_non_python_package(tmp_path: Path) -> None:
    (tmp_path / "packages/jsonly").mkdir(parents=True)
    _touch(tmp_path / "packages/jsonly/package.json")
    _touch(tmp_path / "packages/pyonly/src/mod/__init__.py")

    diagnostics = Diagnostics()
    packages = layout.discover(
        {"packages": "packages/*", "require_python": True}, tmp_path, diagnostics
    )

    roots = [p.root for p in packages]
    assert "packages/pyonly" in roots
    assert "packages/jsonly" not in roots
    assert diagnostics.skipped_no_python == ["packages/jsonly"]


def test_require_python_false_keeps_non_python_package(tmp_path: Path) -> None:
    (tmp_path / "packages/jsonly").mkdir(parents=True)
    _touch(tmp_path / "packages/jsonly/package.json")

    packages = layout.discover({"packages": "packages/*", "require_python": False}, tmp_path)

    assert [p.root for p in packages] == ["packages/jsonly"]


def test_missing_conventional_dirs_are_silently_dropped(tmp_path: Path) -> None:
    _touch(tmp_path / "packages/one/src/one_app/__init__.py")

    packages = layout.discover(
        {"packages": "packages/*", "vendor_dirs": ["vendor"], "test_dirs": ["tests"]},
        tmp_path,
    )

    assert packages[0].vendor_paths == []
    assert packages[0].test_paths == []
