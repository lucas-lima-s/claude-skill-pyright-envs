from __future__ import annotations

import json
from pathlib import Path

import gen_pyright_envs


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def _write_minimal_workspace(tmp_path: Path) -> Path:
    _touch(tmp_path / "packages/one/src/one_app/__init__.py")
    config_path = tmp_path / "pyright-envs.toml"
    config_path.write_text(
        """
root = "."
out = "pyrightconfig.json"
include = ["packages"]

[discovery]
provider = "layout"

[discovery.layout]
packages = "packages/*"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return config_path


def test_missing_config_file_exits_2(tmp_path: Path, capsys) -> None:
    exit_code = gen_pyright_envs.main(["--config", str(tmp_path / "nonexistent.toml")])

    assert exit_code == 2
    assert "nonexistent.toml" in capsys.readouterr().err


def test_no_config_found_by_walking_up_exits_2(tmp_path: Path, capsys) -> None:
    isolated = tmp_path / "isolated"
    isolated.mkdir()

    exit_code = gen_pyright_envs.main(["--root", str(isolated)])

    assert exit_code == 2
    err = capsys.readouterr().err
    assert "pyright-envs.toml" in err
    assert str(isolated) in err


def test_unknown_top_level_key_exits_2(tmp_path: Path, capsys) -> None:
    config_path = tmp_path / "pyright-envs.toml"
    config_path.write_text(
        'root = "."\nnot_a_real_key = true\n\n[discovery]\nprovider = "layout"\n',
        encoding="utf-8",
    )

    exit_code = gen_pyright_envs.main(["--config", str(config_path)])

    assert exit_code == 2
    assert "not_a_real_key" in capsys.readouterr().err


def test_check_mode_is_clean_after_a_fresh_generate(tmp_path: Path) -> None:
    config_path = _write_minimal_workspace(tmp_path)
    out_path = tmp_path / "pyrightconfig.json"

    assert gen_pyright_envs.main(["--config", str(config_path), "--out", str(out_path)]) == 0
    check_args = ["--config", str(config_path), "--out", str(out_path), "--check"]
    assert gen_pyright_envs.main(check_args) == 0


def test_check_mode_detects_drift(tmp_path: Path, capsys) -> None:
    config_path = _write_minimal_workspace(tmp_path)
    out_path = tmp_path / "pyrightconfig.json"
    gen_pyright_envs.main(["--config", str(config_path), "--out", str(out_path)])

    out_path.write_text("// tampered\n{}\n", encoding="utf-8")

    exit_code = gen_pyright_envs.main(
        ["--config", str(config_path), "--out", str(out_path), "--check"]
    )

    assert exit_code == 1
    assert "tampered" in capsys.readouterr().err


def test_stdout_output_is_deterministic_across_runs(tmp_path: Path, capsys) -> None:
    config_path = _write_minimal_workspace(tmp_path)

    gen_pyright_envs.main(["--config", str(config_path), "--out", "-", "--quiet"])
    first = capsys.readouterr().out
    gen_pyright_envs.main(["--config", str(config_path), "--out", "-", "--quiet"])
    second = capsys.readouterr().out

    assert first == second


def test_header_has_no_absolute_path_or_timestamp(tmp_path: Path, capsys) -> None:
    config_path = _write_minimal_workspace(tmp_path)

    gen_pyright_envs.main(["--config", str(config_path), "--out", "-", "--quiet"])
    out = capsys.readouterr().out
    header = out.splitlines()[0]

    assert header.startswith("//")
    assert str(tmp_path) not in header


def test_generated_json_is_valid_and_has_catch_all(tmp_path: Path, capsys) -> None:
    config_path = _write_minimal_workspace(tmp_path)

    gen_pyright_envs.main(["--config", str(config_path), "--out", "-", "--quiet"])
    out = capsys.readouterr().out
    data = json.loads(out[out.index("{") :])

    roots = [env["root"] for env in data["executionEnvironments"]]
    assert "packages/one" in roots
    assert roots[-1] == "packages"
