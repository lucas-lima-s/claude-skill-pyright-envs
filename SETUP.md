# Setup

This project has no machine-specific configuration and no required environment
variables. It only needs a Python interpreter.

## Requirements

- Python 3.11 or newer, on `PATH`.
- [`uv`](https://docs.astral.sh/uv/) for the dev workflow (`uv sync`, `uv run ...`), or
  plain `pip install -r requirements-dev.txt` if you prefer a manually managed
  virtual environment.
- No runtime dependencies: `scripts/gen_pyright_envs.py` and everything under
  `scripts/providers/` are stdlib-only (`argparse`, `json`, `pathlib`, `re`, `tomllib`,
  `xml.etree.ElementTree`, `fnmatch`).
- Node.js and `npx` are only needed for the optional, network-dependent real-Pyright
  cross-check described in the test plan; every other check runs without them.

## First run

```bash
git clone https://github.com/lucas-lima-s/claude-skill-pyright-envs.git
cd claude-skill-pyright-envs
uv sync --dev
uv run pytest -q
```

## Using it in another project

Copy `pyright-envs.example.toml` into the target workspace as `pyright-envs.toml`, adjust
it to match that workspace's layout (see `README.md` for the full configuration
reference), and run:

```bash
python /path/to/scripts/gen_pyright_envs.py
```

There is nothing to point at a specific machine, account, or credential — every path in
the configuration is relative to the workspace root the tool is pointed at.

## As a Claude Code skill

Copy this repository's root (or symlink it) into your Claude Code skills directory so
`SKILL.md` is discoverable, for example `~/.claude/skills/pyright-envs/`. No further
configuration is required; the skill only shells out to the local Python interpreter and
reads/writes files inside the target workspace.
