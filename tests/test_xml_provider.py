from __future__ import annotations

from pathlib import Path

import pytest
from providers import xml_cfg
from providers.common import PyrightEnvsError

LAUNCHER = """<?xml version="1.0" encoding="utf-8"?>
<launcher>
  <group name="Process">
    <key name="Arguments">
      <array>
        <string>runmodule.py</string>
        <string>../packages/widget/src</string>
        <string>../packages/widget/vendor</string>
        <string>widget_shared.pkg</string>
      </array>
    </key>
  </group>
</launcher>
"""

BASE_CFG = {
    "files": "deploy/*/launcher*.xml",
    "path_list_selector": ".//group[@name='Process']/key[@name='Arguments']/array/string",
    "skip_first_if_matches": r"^run.*\.py$",
    "root_pattern": r"^\.\./packages/(?P<name>[^/]+)/src/?$",
    "root_template": "packages/{name}",
    "path_prefix_strip": "../",
}


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def _write_fixture(tmp_path: Path) -> None:
    (tmp_path / "deploy/widget").mkdir(parents=True)
    (tmp_path / "deploy/widget/launcher.xml").write_text(LAUNCHER, encoding="utf-8")
    _touch(tmp_path / "packages/widget/src/widget_app/__init__.py")
    _touch(tmp_path / "packages/widget/vendor/sharedlib/__init__.py")
    _touch(tmp_path / "shared/widget_shared/__init__.py")


def test_extracts_root_via_pattern_and_strips_prefix(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    cfg = {**BASE_CFG, "suffix_map": {".pkg": "shared/{name}"}}

    packages = xml_cfg.discover(cfg, tmp_path)

    assert len(packages) == 1
    assert packages[0].root == "packages/widget"
    assert "packages/widget/src" in packages[0].source_paths


def test_skip_first_if_matches_drops_leading_script_argument(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    cfg = {**BASE_CFG, "suffix_map": {".pkg": "shared/{name}"}}

    packages = xml_cfg.discover(cfg, tmp_path)

    assert not any("runmodule" in p for p in packages[0].source_paths)
    assert not any("runmodule" in p for p in packages[0].vendor_paths)


def test_suffix_map_template_substitutes_name(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    cfg = {**BASE_CFG, "suffix_map": {".pkg": "shared/{name}"}}

    packages = xml_cfg.discover(cfg, tmp_path)

    assert "shared/widget_shared" in packages[0].source_paths


def test_vendor_segment_is_bucketed_as_vendor_path(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    cfg = {**BASE_CFG, "suffix_map": {".pkg": "shared/{name}"}}

    packages = xml_cfg.discover(cfg, tmp_path)

    assert packages[0].vendor_paths == ["packages/widget/vendor"]


def test_malformed_xml_raises_clear_error(tmp_path: Path) -> None:
    (tmp_path / "deploy/broken").mkdir(parents=True)
    (tmp_path / "deploy/broken/launcher.xml").write_text("<launcher><unclosed>", encoding="utf-8")
    cfg = {**BASE_CFG, "suffix_map": {}}

    with pytest.raises(PyrightEnvsError, match="malformed XML"):
        xml_cfg.discover(cfg, tmp_path)
