from __future__ import annotations

from sharedlib import VERSION


def test_alpha_uses_alpha_copy() -> None:
    assert VERSION == "alpha-copy"
