from __future__ import annotations

from pathlib import Path

from providers import manifest
from providers.common import Diagnostics


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def test_keeps_explicit_paths_verbatim_and_in_order(tmp_path: Path) -> None:
    _touch(tmp_path / "packages/one/src/one_app/__init__.py")
    _touch(tmp_path / "packages/one/vendor/sharedlib/__init__.py")
    _touch(tmp_path / "shared/kernel/__init__.py")

    cfg = {
        "packages": {
            "one": {
                "root": "packages/one",
                "extra_paths": [
                    "packages/one/src",
                    "packages/one/vendor",
                    "shared/kernel",
                ],
            }
        }
    }

    packages = manifest.discover(cfg, tmp_path)

    assert len(packages) == 1
    assert packages[0].root == "packages/one"
    assert packages[0].source_paths == [
        "packages/one/src",
        "packages/one/vendor",
        "shared/kernel",
    ]


def test_nonexistent_paths_are_dropped(tmp_path: Path) -> None:
    _touch(tmp_path / "packages/one/src/one_app/__init__.py")

    cfg = {
        "packages": {
            "one": {
                "root": "packages/one",
                "extra_paths": ["packages/one/src", "packages/one/does-not-exist"],
            }
        }
    }

    packages = manifest.discover(cfg, tmp_path)

    assert packages[0].source_paths == ["packages/one/src"]


def test_package_with_no_python_is_skipped_and_reported(tmp_path: Path) -> None:
    _touch(tmp_path / "packages/jsonly/index.js")

    cfg = {
        "packages": {
            "jsonly": {"root": "packages/jsonly", "extra_paths": []},
        }
    }
    diagnostics = Diagnostics()

    packages = manifest.discover(cfg, tmp_path, diagnostics)

    assert packages == []
    assert diagnostics.skipped_no_python == ["packages/jsonly"]
