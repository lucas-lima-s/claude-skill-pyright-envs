from __future__ import annotations

from pathlib import Path

from .common import Diagnostics, Package, dedup, existing, has_python


def discover(cfg: dict, root: Path, diagnostics: Diagnostics | None = None) -> list[Package]:
    pattern = cfg.get("packages", "packages/*")
    source_dirs = cfg.get("source_dirs", ["src"])
    vendor_dirs = cfg.get("vendor_dirs", ["vendor"])
    test_dirs = cfg.get("test_dirs", ["tests", "test"])
    require_python = cfg.get("require_python", True)
    skip_prefixes = cfg.get("skip_prefixes", ["_", "."])

    packages: list[Package] = []
    for candidate in sorted(root.glob(pattern)):
        if not candidate.is_dir():
            continue
        name = candidate.name
        if any(name.startswith(prefix) for prefix in skip_prefixes):
            continue

        pkg_root = candidate.relative_to(root).as_posix()
        source_paths = existing(root, [f"{pkg_root}/{d}" for d in source_dirs])
        vendor_paths = existing(root, [f"{pkg_root}/{d}" for d in vendor_dirs])
        test_paths = existing(root, [f"{pkg_root}/{d}" for d in test_dirs])

        if require_python and not has_python(
            root, [pkg_root, *source_paths, *vendor_paths, *test_paths]
        ):
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
