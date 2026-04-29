"""Tests for the @resilient decorator and affective stack traces."""

from __future__ import annotations

import re

from selfaware import Affect, Mind, format_exception, resilient


def test_resilient_retries_under_fear():
    mind = Mind()
    mind.excite(Affect.FEAR, 0.7)

    attempts = {"n": 0}

    @resilient(
        on_error={Affect.FEAR: "retry_cautiously", Affect.RAGE: "change_strategy"},
        fallback=lambda: "fallback",
        max_retries=4,
        backoff=0.0,
        mind=mind,
    )
    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise TimeoutError("transient")
        return "ok"

    assert flaky() == "ok"
    assert attempts["n"] == 3


def test_resilient_changes_strategy_under_rage():
    mind = Mind()
    mind.excite(Affect.RAGE, 0.9)

    @resilient(
        on_error={Affect.RAGE: "change_strategy"},
        fallback=lambda: "fallback",
        max_retries=4,
        backoff=0.0,
        mind=mind,
    )
    def always_fails():
        raise ConnectionRefusedError()

    assert always_fails() == "fallback"


def test_format_exception_contains_dominant_affect():
    mind = Mind()
    mind.excite(Affect.GRIEF, 0.6)
    try:
        {}["missing"]
    except KeyError as exc:
        rendered = format_exception(exc, mind=mind, colour=False)
    assert "Affective trace" in rendered
    assert re.search(r"grief\s+\d", rendered)


def test_format_exception_includes_reflection_line():
    mind = Mind()
    try:
        raise ConnectionRefusedError("upstream")
    except ConnectionRefusedError as exc:
        rendered = format_exception(exc, mind=mind, colour=False)
    assert "reflection:" in rendered
