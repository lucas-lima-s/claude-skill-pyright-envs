from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree as ET

from .common import Diagnostics, Package, PyrightEnvsError, dedup, existing, has_python


def _bucket_for(path: str) -> str:
    segments = path.split("/")
    if "vendor" in segments:
        return "vendor"
    if segments and segments[-1] in ("tests", "test"):
        return "test"
    return "source"


def _resolve_entry(entry: str, suffix_map: dict, path_prefix_strip: str) -> str:
    suffix_hit = next((suffix for suffix in suffix_map if entry.endswith(suffix)), None)
    if suffix_hit is not None:
        stem = entry[: -len(suffix_hit)]
        return suffix_map[suffix_hit].format(name=stem)
    if path_prefix_strip and entry.startswith(path_prefix_strip):
        return entry[len(path_prefix_strip) :]
    return entry


def discover(cfg: dict, root: Path, diagnostics: Diagnostics | None = None) -> list[Package]:
    files_pattern = cfg["files"]
    selector = cfg["path_list_selector"]
    skip_first_if_matches = cfg.get("skip_first_if_matches")
    root_pattern = re.compile(cfg["root_pattern"])
    root_template = cfg.get("root_template", "packages/{name}")
    path_prefix_strip = cfg.get("path_prefix_strip", "")
    suffix_map: dict = cfg.get("suffix_map", {})

    packages: list[Package] = []

    for xml_file in sorted(root.glob(files_pattern)):
        try:
            tree = ET.parse(xml_file)
        except ET.ParseError as exc:
            raise PyrightEnvsError(f"malformed XML in {xml_file}: {exc}") from exc

        entries = [el.text.strip() for el in tree.findall(selector) if el.text and el.text.strip()]

        if skip_first_if_matches and entries and re.match(skip_first_if_matches, entries[0]):
            entries = entries[1:]

        pkg_name = None
        for entry in entries:
            match = root_pattern.match(entry)
            if match:
                pkg_name = match.group("name")
                break
        if pkg_name is None:
            continue

        pkg_root = root_template.format(name=pkg_name)

        buckets: dict[str, list[str]] = {"source": [], "vendor": [], "test": []}
        for entry in entries:
            resolved = _resolve_entry(entry, suffix_map, path_prefix_strip)
            buckets[_bucket_for(resolved)].append(resolved)

        source_paths = existing(root, buckets["source"])
        vendor_paths = existing(root, buckets["vendor"])
        test_paths = existing(root, buckets["test"])

        if not has_python(root, [pkg_root, *source_paths, *vendor_paths, *test_paths]):
            if diagnostics is not None:
                diagnostics.skipped_no_python.append(pkg_root)
            continue

        packages.append(
            Package(
                root=pkg_root,
                source_paths=dedup(source_paths),
                vendor_paths=dedup(vendor_paths),
                test_paths=dedup(test_paths),
            )
        )

    return packages
