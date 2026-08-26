from __future__ import annotations

import argparse
import difflib
import json
import sys
import tomllib
from pathlib import Path

from providers import PROVIDERS
from providers.common import Diagnostics, Package, PyrightEnvsError, dedup, existing

CONFIG_FILENAME = "pyright-envs.toml"

DEFAULTS = {
    "root": ".",
    "out": "pyrightconfig.json",
    "python_version": "3.11",
    "python_platform": "All",
    "type_checking_mode": "off",
    "include": ["."],
    "exclude": [
        "**/node_modules",
        "**/.venv",
        "**/__pycache__",
        "**/dist",
        "**/build",
        "**/.mypy_cache",
        "**/.ruff_cache",
        "**/.pytest_cache",
    ],
    "shared_roots": [],
    "append_catch_all": True,
}

_DYNAMIC_MAP = "dynamic_map"
_DYNAMIC_LEAF = "dynamic_leaf"

_LAYOUT_SCHEMA = {
    "packages": None,
    "source_dirs": None,
    "vendor_dirs": None,
    "test_dirs": None,
    "require_python": None,
    "skip_prefixes": None,
}

_MANIFEST_PACKAGE_SCHEMA = {"root": None, "extra_paths": None}

_MANIFEST_SCHEMA = {
    "packages": (_DYNAMIC_MAP, _MANIFEST_PACKAGE_SCHEMA),
}

_XML_SCHEMA = {
    "files": None,
    "path_list_selector": None,
    "skip_first_if_matches": None,
    "root_pattern": None,
    "root_template": None,
    "path_prefix_strip": None,
    "suffix_map": (_DYNAMIC_LEAF,),
}

_DISCOVERY_SCHEMA = {
    "provider": None,
    "layout": _LAYOUT_SCHEMA,
    "manifest": _MANIFEST_SCHEMA,
    "xml": _XML_SCHEMA,
}

_ROOT_SCHEMA = {
    "root": None,
    "out": None,
    "python_version": None,
    "python_platform": None,
    "type_checking_mode": None,
    "include": None,
    "exclude": None,
    "shared_roots": None,
    "append_catch_all": None,
    "discovery": _DISCOVERY_SCHEMA,
}


def _validate(cfg: dict, schema: dict, path: str = "") -> None:
    for key, value in cfg.items():
        full = f"{path}.{key}" if path else key
        if key not in schema:
            raise PyrightEnvsError(f"unknown configuration key: {full}")

        node = schema[key]
        if isinstance(node, dict):
            if isinstance(value, dict):
                _validate(value, node, full)
        elif isinstance(node, tuple) and node[0] == _DYNAMIC_MAP:
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    subfull = f"{full}.{subkey}"
                    if isinstance(subvalue, dict):
                        _validate(subvalue, node[1], subfull)
        elif isinstance(node, tuple) and node[0] == _DYNAMIC_LEAF:
            continue


def _find_config(start: Path) -> Path:
    current = start.resolve()
    for directory in [current, *current.parents]:
        candidate = directory / CONFIG_FILENAME
        if candidate.exists():
            return candidate
    raise PyrightEnvsError(f"could not find {CONFIG_FILENAME} by walking up from {start}")


def _load_config(path: Path) -> dict:
    if not path.exists():
        raise PyrightEnvsError(f"config file not found: {path}")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    _validate(data, _ROOT_SCHEMA)
    return data


def _build_environments(
    cfg: dict, root: Path, diagnostics: Diagnostics
) -> tuple[list[dict], list[Package]]:
    discovery_cfg = cfg.get("discovery", {})
    provider_name = discovery_cfg.get("provider")
    if provider_name not in PROVIDERS:
        raise PyrightEnvsError(f"unknown discovery provider: {provider_name!r}")

    provider_cfg = discovery_cfg.get(provider_name, {})
    packages = PROVIDERS[provider_name](provider_cfg, root, diagnostics)

    shared_roots = cfg.get("shared_roots", DEFAULTS["shared_roots"])
    shared_existing = existing(root, shared_roots)
    missing_shared = dedup([p for p in shared_roots if p not in shared_existing])
    for path in missing_shared:
        print(
            f"shared root not found: {path} (imports into it will not resolve)",
            file=sys.stderr,
        )

    envs: list[dict] = []
    for pkg in packages:
        extra_paths = dedup(
            [*pkg.source_paths, *pkg.vendor_paths, *shared_existing, *pkg.test_paths]
        )
        env: dict = {"root": pkg.root}
        if extra_paths:
            env["extraPaths"] = extra_paths
        envs.append(env)

    envs.sort(key=lambda e: (-e["root"].count("/"), e["root"]))

    if cfg.get("append_catch_all", DEFAULTS["append_catch_all"]):
        include = cfg.get("include", DEFAULTS["include"])
        catch_all_root = include[0] if include else "."
        envs.append({"root": catch_all_root})

    return envs, packages


def _render(cfg: dict, envs: list[dict], config_path: Path) -> str:
    body = {
        "include": cfg.get("include", DEFAULTS["include"]),
        "exclude": cfg.get("exclude", DEFAULTS["exclude"]),
        "pythonVersion": cfg.get("python_version", DEFAULTS["python_version"]),
        "pythonPlatform": cfg.get("python_platform", DEFAULTS["python_platform"]),
        "typeCheckingMode": cfg.get("type_checking_mode", DEFAULTS["type_checking_mode"]),
        "executionEnvironments": envs,
    }
    header = f"// Generated by gen_pyright_envs.py from {config_path.name}. Do not edit by hand.\n"
    return header + json.dumps(body, indent=2) + "\n"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="gen_pyright_envs.py")
    parser.add_argument("--config", help="path to pyright-envs.toml")
    parser.add_argument("--root", help="workspace root (defaults to the config file's directory)")
    parser.add_argument("--out", help='output path, or "-" for stdout')
    parser.add_argument("--check", action="store_true", help="verify the output is up to date")
    parser.add_argument("--quiet", action="store_true", help="suppress the stderr summary")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        if args.config:
            config_path = Path(args.config)
            if not config_path.exists():
                raise PyrightEnvsError(f"config file not found: {config_path}")
        else:
            start = Path(args.root) if args.root else Path.cwd()
            config_path = _find_config(start)

        cfg = _load_config(config_path)
        root = (Path(args.root) if args.root else config_path.parent).resolve()

        diagnostics = Diagnostics()
        envs, packages = _build_environments(cfg, root, diagnostics)
        content = _render(cfg, envs, config_path)

        if args.out:
            out_arg = args.out
            out_path = None if out_arg == "-" else Path(out_arg)
        else:
            out_arg = cfg.get("out", DEFAULTS["out"])
            out_path = None if out_arg == "-" else root / out_arg

        if not args.quiet:
            print(
                f"{len(envs)} execution environments generated across {len(packages)} packages; "
                f"{len(diagnostics.skipped_no_python)} packages skipped (no python)",
                file=sys.stderr,
            )

        if args.check:
            if out_path is None:
                raise PyrightEnvsError("--check cannot be combined with --out -")
            existing_content = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
            if existing_content == content:
                return 0
            diff = difflib.unified_diff(
                existing_content.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=str(out_path),
                tofile="<generated>",
            )
            sys.stderr.writelines(diff)
            return 1

        if out_path is None:
            sys.stdout.write(content)
        else:
            out_path.write_text(content, encoding="utf-8", newline="\n")
        return 0
    except PyrightEnvsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
