---
name: pyright-envs
description: Generate a pyrightconfig.json with one executionEnvironment per package so that Go to Definition in a monorepo resolves each file against its own import paths instead of another package's vendored copy of the same module. Use when Ctrl+click jumps into the wrong package, after a hard clean removed pyrightconfig.json, on a fresh clone, or when the set of packages changed. Triggers on "go to definition is going to the wrong package", "regenerate pyrightconfig", "pylance resolves the wrong copy", "regenerar pyrightconfig", "o ctrl+click foi pro pacote errado".
---

## The problem

In a monorepo where several packages each vendor their own copy of the same third-party
module, a single flat Pylance/Pyright index cannot tell which copy a given file should
resolve against. Picture two packages, `alpha` and `beta`, each with their own
`vendor/sharedlib/` directory containing a different build of the same library. Without
per-package isolation, Ctrl+click (Go to Definition) from a file in `alpha` can just as
easily land in `beta`'s copy — whichever one the editor happened to index first. The bug
is silent: imports still resolve, autocomplete still works, but they point at the wrong
file, and refactors made through "Go to Definition" edit the wrong package.

Pyright's `executionEnvironments` setting fixes this: each package gets its own `root`
and its own `extraPaths`, so Pyright resolves imports for a file against that package's
paths only. Hand-writing dozens of these entries for a real monorepo is not something
anyone wants to do by hand, or keep in sync as packages come and go. This tool generates
the whole `executionEnvironments` list from a small config file.

## How the fix works

1. Every discovered package becomes one entry: `{"root": "<package>", "extraPaths": [...]}`.
2. `extraPaths` are ordered source dirs, then vendor dirs, then shared roots, then test
   dirs, deduplicated.
3. A path is only emitted if it exists on disk. A configured shared root that does not
   exist is dropped and reported once on stderr, never silently swallowed.
4. A package with no Python file under any of its candidate paths is skipped, which is
   what keeps a JS-only frontend package out of the generated config.
5. Environments are sorted deepest root first, then alphabetically, because Pyright must
   see the more specific package before its parent to pick the right one.
6. A final catch-all environment can be appended for anything outside the discovered
   packages.
7. The header comment is fixed text naming the tool and the config file used — no
   timestamp, no absolute path, no machine name — so two runs against the same input
   produce byte-identical output and `--check` is meaningful in CI.

## The three discovery providers

- **`layout`** — convention-based. Give it a glob for package roots
  (`packages/*`) and a list of candidate source/vendor/test directory names; it scans
  the filesystem and builds packages from what it finds. Best when packages already
  follow a consistent directory layout.
- **`manifest`** — fully explicit. Each package is declared by name with a `root` and a
  literal `extra_paths` list. Best for a handful of packages, or ones whose layout is too
  irregular for the `layout` provider to infer.
- **`xml`** — generic, selector-driven discovery from launcher-style XML files that
  already encode a package's import paths as command-line arguments. This exists because
  some older monorepos ship exactly this kind of generated launcher, and the paths in it
  are a genuine source of truth worth reusing rather than duplicating by hand. It is
  driven entirely by config: an ElementTree-compatible selector picks out the path list,
  an optional regex drops a leading script argument, a named-group regex derives the
  package root, and an optional suffix map expands symbolic references (for example
  `kernel_utils.pkg`) into real paths.

Adding a fourth provider requires no change to the CLI: every provider module exposes a
single `discover(cfg, root) -> list[Package]` function, and the CLI only needs a new
entry in the provider registry. See `CONTRIBUTING.md`.

## Commands

```bash
python scripts/gen_pyright_envs.py                       # write pyrightconfig.json
python scripts/gen_pyright_envs.py --config path.toml     # use a specific config file
python scripts/gen_pyright_envs.py --out -                 # print to stdout instead
python scripts/gen_pyright_envs.py --check                 # exit 1 if the file is stale
```

`--config` defaults to `pyright-envs.toml`, found by walking up from `--root` (which
itself defaults to the current directory). `--check` regenerates the config in memory and
compares it byte-for-byte with what is on disk — use it in CI to catch a stale committed
`pyrightconfig.json`, or drop it and add `pyrightconfig.json` to `.git/info/exclude`
instead if the workspace prefers not to commit generated files at all. Both are
reasonable; committing is the better default for a team, since every teammate then gets
correct navigation from a fresh clone without an extra step.

## After regenerating

Pyright and Pylance cache the previous configuration. After running the generator, reload
the editor window or run "Python: Restart Language Server" so the new
`executionEnvironments` take effect.

## Honest reporting

Two situations are reported rather than hidden:

- A configured shared root that does not exist on disk prints
  `shared root not found: <path> (imports into it will not resolve)` on stderr, and the
  path is left out of every environment that would have referenced it.
- A package with no Python file anywhere under its candidate paths is skipped and counted
  in the run summary, rather than emitted as an empty, useless environment.
