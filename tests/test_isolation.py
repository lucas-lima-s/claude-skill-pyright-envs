from __future__ import annotations

import json
from pathlib import Path

import gen_pyright_envs

SAMPLE_MONOREPO = Path(__file__).resolve().parent.parent / "examples" / "sample-monorepo"


def _generate(config_name: str, capsys) -> dict:
    config_path = SAMPLE_MONOREPO / config_name
    exit_code = gen_pyright_envs.main(["--config", str(config_path), "--out", "-", "--quiet"])
    assert exit_code == 0
    out = capsys.readouterr().out
    body = out[out.index("{") :]
    return json.loads(body)


def _envs_by_root(data: dict) -> dict[str, list[str]]:
    return {env["root"]: env.get("extraPaths", []) for env in data["executionEnvironments"]}


def test_layout_alpha_and_beta_do_not_leak_into_each_other(capsys) -> None:
    envs = _envs_by_root(_generate("pyright-envs.layout.toml", capsys))

    assert "packages/alpha/vendor" in envs["packages/alpha"]
    assert not any("beta" in p for p in envs["packages/alpha"])

    assert "packages/beta/vendor" in envs["packages/beta"]
    assert not any("alpha" in p for p in envs["packages/beta"])


def test_layout_gamma_uses_shared_kernel_without_vendor(capsys) -> None:
    envs = _envs_by_root(_generate("pyright-envs.layout.toml", capsys))

    assert "shared-kernel/src" in envs["packages/gamma"]
    assert not any("vendor" in p for p in envs["packages/gamma"])


def test_layout_frontend_produces_no_environment(capsys) -> None:
    envs = _envs_by_root(_generate("pyright-envs.layout.toml", capsys))

    assert all("frontend" not in root for root in envs)


def test_manifest_alpha_and_beta_do_not_leak_into_each_other(capsys) -> None:
    envs = _envs_by_root(_generate("pyright-envs.manifest.toml", capsys))

    assert "packages/alpha/vendor" in envs["packages/alpha"]
    assert not any("beta" in p for p in envs["packages/alpha"])
    assert "packages/beta/vendor" in envs["packages/beta"]
    assert not any("alpha" in p for p in envs["packages/beta"])


def test_xml_delta_resolves_via_launcher(capsys) -> None:
    envs = _envs_by_root(_generate("pyright-envs.xml.toml", capsys))

    assert "packages/delta" in envs
    assert "packages/delta/src" in envs["packages/delta"]
    assert "packages/delta/vendor" in envs["packages/delta"]
    assert "shared-kernel/src" in envs["packages/delta"]
