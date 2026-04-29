"""Tests for the affect data model and dynamics."""

from __future__ import annotations

from selfaware.affects import (
    Affect,
    AffectVector,
    DECAY_PER_SEC,
    Feeling,
    RESTING_TONE,
    feelings_of,
    step_dynamics,
)


def test_affect_vector_defaults_to_resting_tone():
    v = AffectVector()
    for a in Affect:
        assert v[a] == RESTING_TONE[a]


def test_excite_clips_at_one():
    v = AffectVector()
    v.excite(Affect.RAGE, 5.0)
    assert v[Affect.RAGE] == 1.0


def test_soothe_clips_at_zero():
    v = AffectVector()
    v.excite(Affect.FEAR, 0.5)
    v.soothe(Affect.FEAR, 5.0)
    assert v[Affect.FEAR] == 0.0


def test_dynamics_decay_toward_resting_tone():
    v = AffectVector()
    v.excite(Affect.RAGE, 0.8)
    initial = v[Affect.RAGE]
    after = step_dynamics(v, dt=2.0)
    assert after[Affect.RAGE] < initial
    assert after[Affect.RAGE] >= RESTING_TONE[Affect.RAGE]


def test_cross_inhibition_drains_target_affect():
    v = AffectVector()
    v.excite(Affect.RAGE, 0.9)
    v.excite(Affect.FEAR, 0.6)
    after = step_dynamics(v, dt=1.0)
    assert after[Affect.FEAR] < v[Affect.FEAR]


def test_dominant_returns_strongest():
    v = AffectVector()
    v.excite(Affect.GRIEF, 0.7)
    v.excite(Affect.FEAR, 0.4)
    a, val = v.dominant()
    assert a == Affect.GRIEF
    assert val >= 0.7


def test_mood_summary_calm_when_low():
    v = AffectVector()
    assert v.mood() == "calm"


def test_mood_summary_uses_dominant():
    v = AffectVector()
    v.excite(Affect.GRIEF, 0.6)
    assert "bereft" in v.mood()


def test_feelings_of_handles_missing_protocol():
    assert feelings_of(object()) == ()


def test_feelings_of_accepts_single_feeling():
    class X:
        def __feel__(self):
            return Feeling(Affect.LUST, 0.4, "warm")

    fs = list(feelings_of(X()))
    assert len(fs) == 1
    assert fs[0].affect == Affect.LUST
    assert fs[0].intensity == 0.4


def test_feelings_of_accepts_iterable():
    class X:
        def __feel__(self):
            return [Feeling(Affect.SEEKING, 0.3), Feeling(Affect.PLAY, 0.2)]

    fs = list(feelings_of(X()))
    assert {f.affect for f in fs} == {Affect.SEEKING, Affect.PLAY}


def test_feelings_of_swallows_exceptions():
    class X:
        def __feel__(self):
            raise RuntimeError("nope")

    assert feelings_of(X()) == ()


def test_decay_constants_are_positive():
    for a in Affect:
        assert DECAY_PER_SEC[a] > 0
