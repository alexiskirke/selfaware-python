"""Tests for the affect-gradient profiler."""

from __future__ import annotations

from selfaware import Affect, AffectProfiler, Mind


def test_profiler_records_affect_deltas():
    mind = Mind()
    profiler = AffectProfiler(mind)

    with profiler.scope("scary"):
        mind.excite(Affect.FEAR, 0.4)

    records = profiler.records()
    assert len(records) == 1
    rec = records[0]
    assert rec.label == "scary"
    assert rec.calls == 1
    assert rec.deltas[Affect.FEAR] >= 0.3


def test_profiler_report_is_string_and_lists_scopes():
    mind = Mind()
    profiler = AffectProfiler(mind)

    with profiler.scope("a"):
        mind.excite(Affect.RAGE, 0.3)
    with profiler.scope("b"):
        mind.excite(Affect.LUST, 0.2)

    out = profiler.report()
    assert "scope" in out
    assert "a" in out and "b" in out
