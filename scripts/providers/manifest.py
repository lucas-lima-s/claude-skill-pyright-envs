from __future__ import annotations

from pathlib import Path

from .common import Diagnostics, Package, dedup, existing, has_python


def discover(cfg: dict, root: Path, diagnostics: Diagnostics | None = None) -> list[Package]:
    packages_cfg: dict = cfg.get("packages", {})
    packages: list[Package] = []

    for name in sorted(packages_cfg):
        entry = packages_cfg[name]
        pkg_root = entry["root"]
        extra_paths = existing(root, entry.get("extra_paths", []))

        if not has_python(root, [pkg_root, *extra_paths]):
            if diagnostics is not None:
                diagnostics.skipped_no_python.append(pkg_root)
            continue

        packages.append(
            Package(
                root=pkg_root,
                source_paths=dedup(extra_paths),
                vendor_paths=[],
                test_paths=[],
            )
        )
    return packages
