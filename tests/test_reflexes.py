"""Tests for bundled reflexes."""

from __future__ import annotations

import time

from selfaware import Affect, Mind
from selfaware.reflexes import (
    Caretaker,
    CircuitBreaker,
    CircuitOpen,
    DefensiveMode,
    SpeculativeMemoizer,
)


def test_circuit_breaker_opens_on_rage():
    mind = Mind()
    breaker = CircuitBreaker("svc", reset_at=0.2, cooldown=0.1)
    mind.bind(Affect.RAGE, 0.5, breaker)

    @breaker.guard
    def call():
        return "ok"

    assert call() == "ok"
    mind.excite(Affect.RAGE, 0.9)
    mind.tick()
    try:
        call()
    except CircuitOpen:
        pass
    else:
        raise AssertionError("breaker should have opened")


def test_circuit_breaker_recovers_after_cooldown():
    mind = Mind()
    breaker = CircuitBreaker("svc", reset_at=0.2, cooldown=0.05)
    mind.bind(Affect.RAGE, 0.5, breaker)

    @breaker.guard
    def call():
        return "ok"

    mind.excite(Affect.RAGE, 0.9)
    mind.tick()
    try:
        call()
    except CircuitOpen:
        pass
    # Decay RAGE and let cooldown pass
    mind.soothe(Affect.RAGE, 1.0)
    time.sleep(0.1)
    mind.tick()
    assert call() == "ok"


def test_defensive_mode_shrinks_batch_under_fear():
    mind = Mind()
    defensive = DefensiveMode(default_batch_size=100, min_batch_size=10)
    mind.bind(Affect.FEAR, 0.5, defensive)
    assert defensive.batch_size == 100
    mind.excite(Affect.FEAR, 0.9)
    mind.tick()
    defensive.update_from(mind)
    assert defensive.batch_size < 100
    assert defensive.validate is True


def test_speculative_memoizer_caches_only_when_engaged():
    mind = Mind()
    memo = SpeculativeMemoizer(max_size=8)
    mind.bind(Affect.SEEKING, 0.3, memo)

    calls = {"n": 0}

    @memo.cache
    def expensive(x):
        calls["n"] += 1
        return x * 2

    # Not engaged yet — but cache only admits when engaged. So 2 calls = 2 hits to underlying fn.
    expensive(1)
    expensive(1)
    assert calls["n"] == 2

    # Engage it.
    mind.excite(Affect.SEEKING, 0.6)
    mind.tick()
    expensive(2)
    expensive(2)
    expensive(2)
    # First call computes and admits; subsequent calls hit cache.
    assert calls["n"] == 3


def test_caretaker_runs_charges_in_priority_order():
    mind = Mind()
    caretaker = Caretaker()
    order = []
    caretaker.adopt(lambda: order.append("low"), priority=0)
    caretaker.adopt(lambda: order.append("high"), priority=10)
    caretaker.adopt(lambda: order.append("mid"), priority=5)

    mind.bind(Affect.CARE, 0.5, caretaker)
    mind.excite(Affect.CARE, 0.9)
    mind.tick()
    assert order == ["high", "mid", "low"]


def test_caretaker_continues_through_failing_charges():
    mind = Mind()
    caretaker = Caretaker()
    out = []

    def boom():
        raise RuntimeError("first one fails")

    caretaker.adopt(boom, priority=10)
    caretaker.adopt(lambda: out.append("ran"), priority=5)

    mind.bind(Affect.CARE, 0.5, caretaker)
    mind.excite(Affect.CARE, 0.9)
    mind.tick()
    assert out == ["ran"]
