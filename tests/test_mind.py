"""Tests for the Mind orchestrator."""

from __future__ import annotations

import time

from selfaware import Affect, Mind, Sentient, Feeling
from selfaware.sensors import ErrorSensor, LatencySensor


def test_mind_starts_calm():
    mind = Mind()
    assert mind.mood() == "calm"


def test_mind_excite_changes_dominant():
    mind = Mind()
    mind.excite(Affect.GRIEF, 0.7)
    a, _ = mind.affects.dominant()
    assert a == Affect.GRIEF


def test_mind_attaches_sensor_and_polls_on_tick():
    mind = Mind()
    sensor = LatencySensor(target_ms=10, danger_ms=50)
    sensor.record(20)
    sensor.record(30)
    mind.attach(sensor)
    before = mind.affects[Affect.RAGE]
    mind.tick()
    assert mind.affects[Affect.RAGE] >= before


def test_reflex_fires_when_threshold_crossed():
    mind = Mind()
    fired = []

    def reflex(m, affect, value):
        fired.append((affect, value))

    mind.bind(Affect.RAGE, 0.5, reflex)
    mind.excite(Affect.RAGE, 0.8)
    mind.tick()
    assert len(fired) == 1
    assert fired[0][0] == Affect.RAGE


def test_reflex_does_not_fire_twice_without_hysteresis_drop():
    mind = Mind()
    fired = []
    mind.bind(Affect.RAGE, 0.5, lambda m, a, v: fired.append(v), hysteresis=0.1)
    mind.excite(Affect.RAGE, 0.9)
    mind.tick()
    mind.excite(Affect.RAGE, 0.05)
    mind.tick()
    assert len(fired) == 1


def test_reflex_refires_after_dropping_below_hysteresis():
    mind = Mind()
    fired = []
    mind.bind(Affect.RAGE, 0.5, lambda m, a, v: fired.append(v), hysteresis=0.1)
    mind.excite(Affect.RAGE, 0.9)
    mind.tick()
    mind.soothe(Affect.RAGE, 0.9)
    mind.tick()
    mind.excite(Affect.RAGE, 0.9)
    mind.tick()
    assert len(fired) == 2


def test_feel_protocol_integrates_with_mind():
    class X(Sentient):
        def _dominant_affect(self):
            return Affect.LUST

        def _dominant_intensity(self):
            return 0.4

    mind = Mind()
    mind.feel(X())
    assert mind.affects[Affect.LUST] >= 0.4


def test_history_records_excitations():
    mind = Mind()
    mind.excite(Affect.SEEKING, 0.3, note="explore")
    history = mind.history()
    assert any("explore" in e.note for e in history)


def test_trajectory_aggregates_recent_changes():
    mind = Mind()
    mind.excite(Affect.FEAR, 0.5)
    mind.excite(Affect.FEAR, 0.2)
    traj = mind.trajectory(last=10)
    affects_seen = {a for a, _ in traj}
    assert Affect.FEAR in affects_seen


def test_observing_context_manager_runs_background_loop():
    mind = Mind()
    with mind.observing(period=0.05):
        time.sleep(0.15)
    # Just verify it doesn't deadlock/raise; bg thread should be cleaned up.
    assert mind._bg_thread is None
