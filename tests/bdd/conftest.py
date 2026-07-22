"""pytest-bdd fixtures and hooks for the executable RULES.md spec."""

import pytest


@pytest.fixture
def context() -> dict:
    """Mutable per-scenario state threaded through the Given/When/Then steps."""
    return {"config": {}, "profile": None, "source": None, "violations": None}


def pytest_bdd_apply_tag(tag, function):
    """Map the ``@skip`` feature tag (blocked/planned rules) onto pytest skip."""
    if tag == "skip":
        pytest.mark.skip(reason="blocked/planned rule — not yet implemented")(function)
        return True
    return None
