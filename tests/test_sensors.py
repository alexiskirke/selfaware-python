"""Tests for sensors."""

from __future__ import annotations

from selfaware import Affect
from selfaware.sensors import (
    CacheSensor,
    ConnectionSensor,
    ErrorSensor,
    LatencySensor,
    NoveltySensor,
)


def test_latency_sensor_emits_rage_above_target():
    s = LatencySensor(target_ms=10, danger_ms=100)
    for ms in (40, 50, 60):
        s.record(ms)
    delta = s.read()
    assert delta is not None
    assert delta.get(Affect.RAGE, 0) > 0


def test_latency_sensor_emits_fear_above_danger():
    s = LatencySensor(target_ms=10, danger_ms=100)
    s.record(500)
    delta = s.read()
    assert delta is not None
    assert delta.get(Affect.FEAR, 0) > 0


def test_latency_sensor_satiety_when_well_under_target():
    s = LatencySensor(target_ms=100, danger_ms=300)
    for _ in range(5):
        s.record(10)
    delta = s.read()
    assert delta is not None
    assert delta.get(Affect.SATIETY, 0) > 0


def test_error_sensor_classifies_connection_as_rage():
    s = ErrorSensor()
    s.record(ConnectionRefusedError())
    delta = s.read()
    assert delta is not None
    assert delta.get(Affect.RAGE, 0) > 0


def test_error_sensor_escalates_repeated_connections():
    s = ErrorSensor()
    for _ in range(5):
        s.record(ConnectionRefusedError())
    delta = s.read()
    assert delta is not None
    # Repeated connection failures should also drive FEAR.
    assert delta.get(Affect.FEAR, 0) > 0


def test_error_sensor_grief_for_lookup():
    s = ErrorSensor()
    s.record(KeyError("x"))
    delta = s.read()
    assert delta is not None
    assert delta.get(Affect.GRIEF, 0) > 0


def test_cache_sensor_lust_on_high_hit_rate():
    s = CacheSensor()
    s.hit(8)
    s.miss(2)
    delta = s.read()
    assert delta is not None
    assert delta.get(Affect.LUST, 0) > 0


def test_cache_sensor_seeking_on_high_miss_rate():
    s = CacheSensor()
    s.hit(1)
    s.miss(9)
    delta = s.read()
    assert delta is not None
    assert delta.get(Affect.SEEKING, 0) > 0


def test_novelty_sensor_seeks_on_new_tags():
    s = NoveltySensor()
    s.mark("a")
    s.mark("b")
    s.mark("c")
    delta = s.read()
    assert delta is not None
    assert delta.get(Affect.SEEKING, 0) > 0


def test_novelty_sensor_satiety_on_familiar_only():
    s = NoveltySensor()
    s.mark("a")
    s.read()  # consume
    s.mark("a")
    s.mark("a")
    delta = s.read()
    assert delta is not None
    assert delta.get(Affect.SATIETY, 0) > 0


def test_connection_sensor_grief_on_drop():
    s = ConnectionSensor()
    s.up("db")
    s.read()
    s.down("db")
    delta = s.read()
    assert delta is not None
    assert delta.get(Affect.GRIEF, 0) > 0


def test_connection_sensor_lust_on_reconnect():
    s = ConnectionSensor()
    s.down("db")
    s.read()
    s.up("db")
    delta = s.read()
    assert delta is not None
    assert delta.get(Affect.LUST, 0) > 0
