# Contributing

## Provider contract

Every discovery provider lives in its own module under `scripts/providers/` and exposes
exactly one function:

```python
def discover(cfg: dict, root: Path, diagnostics: Diagnostics | None = None) -> list[Package]: ...
```

- `cfg` is that provider's own sub-table from `pyright-envs.toml` (e.g.
  `discovery.layout`), never the full config.
- `root` is the resolved workspace root every returned path must be relative to.
- `diagnostics`, when given, is where a provider records a package it chose not to
  return (currently: `diagnostics.skipped_no_python`), so the CLI can report it in the
  run summary without the provider needing to print anything itself.
- The return value is a list of `Package` (`root`, `source_paths`, `vendor_paths`,
  `test_paths`), all as root-relative, forward-slash, already-existence-filtered paths.

**Adding a fourth provider requires no change to the CLI.** Write the module, expose
`discover`, and add one line to the `PROVIDERS` dict in `scripts/providers/__init__.py`:

```python
PROVIDERS = {
    "layout": layout.discover,
    "manifest": manifest.discover,
    "xml": xml_cfg.discover,
    "your_provider": your_provider.discover,
}
```

The CLI's sorting, deduplication, existence filtering, shared-root injection, catch-all
entry, and header rendering are all shared and provider-agnostic — a new provider only
needs to return correct `Package` objects.

## Code style

- `from __future__ import annotations` at the top of every module.
- PEP 585 / PEP 604 annotations (`list[str]`, `X | None`) — no `typing.List` or
  `typing.Optional`.
- Standard library only. No new runtime dependency without discussing it first.
- No inline comments. Keep any docstring minimal.
- Formatting and linting via `ruff format` / `ruff check`, both run in CI.

## Tests

- `uv run pytest -q` must pass, and should stay comfortably above the current test count.
- If you add a provider, add a fixture-backed test module for it plus at least one
  isolation-style assertion (no path from one package leaking into another's
  `extraPaths`).
- If you change anything about the generated JSON shape or ordering, regenerate the
  golden files under `examples/sample-monorepo/expected/` and check the diff is the one
  you intended:

```bash
uv run python scripts/gen_pyright_envs.py --config examples/sample-monorepo/pyright-envs.layout.toml --out examples/sample-monorepo/expected/pyrightconfig.layout.json
uv run python scripts/gen_pyright_envs.py --config examples/sample-monorepo/pyright-envs.manifest.toml --out examples/sample-monorepo/expected/pyrightconfig.manifest.json
uv run python scripts/gen_pyright_envs.py --config examples/sample-monorepo/pyright-envs.xml.toml --out examples/sample-monorepo/expected/pyrightconfig.xml.json
```

## Commit style

Conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `ci:`, `chore:`), one logical
change per commit.
