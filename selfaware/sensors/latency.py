"""Latency sensor: maps slow operations to FEAR + RAGE.

Slow operations have two distinct affective meanings depending on whether
they *finish*:

* If a request is merely slow but completing, that is RAGE — work is being
  done but goals are being thwarted. Real organisms get angry when their
  goals are blocked but achievable.
* If a request slows past a threshold and looks like it might fail, that is
  FEAR — anticipation of an outright failure.

We therefore drive both affects, with RAGE rising linearly with the slowdown
and FEAR rising super-linearly once the latency exceeds a "danger" budget.
"""

from __future__ import annotations

from collections import deque
from time import perf_counter
from typing import Deque, Dict, Optional

from ..affects import Affect
from .base import Sensor


class LatencySensor(Sensor):
    """Track recent operation latencies and emit affect deltas.

    Use the :meth:`time` context manager to record real durations::

        latency = LatencySensor(target_ms=50, danger_ms=200)
        with latency.time():
            do_work()
        mind.attach(latency)

    Or call :meth:`record` directly with measured milliseconds.
    """

    name = "latency"

    def __init__(
        self,
        *,
        target_ms: float = 50.0,
        danger_ms: float = 200.0,
        window: int = 32,
    ) -> None:
        self.target_ms = target_ms
        self.danger_ms = danger_ms
        self._samples: Deque[float] = deque(maxlen=window)

    def record(self, ms: float) -> None:
        self._samples.append(ms)

    def time(self) -> "_TimeCtx":
        return _TimeCtx(self)

    def read(self) -> Optional[Dict[Affect, float]]:
        if not self._samples:
            return None
        samples = list(self._samples)
        self._samples.clear()
        avg = sum(samples) / len(samples)
        peak = max(samples)
        out: Dict[Affect, float] = {}

        # RAGE: linear in how much we exceed target. Capped so a single bad
        # batch doesn't explode the whole vector.
        if avg > self.target_ms:
            out[Affect.RAGE] = min(0.25, (avg / self.target_ms - 1.0) * 0.10)

        # FEAR: kicks in only past the danger budget, super-linearly.
        if peak > self.danger_ms:
            ratio = peak / self.danger_ms
            out[Affect.FEAR] = min(0.30, (ratio - 1.0) ** 1.5 * 0.20)

        # SATIETY: things were comfortably under target -> a small completion signal.
        if avg < self.target_ms * 0.5 and peak < self.target_ms:
            out[Affect.SATIETY] = 0.05

        return out or None


class _TimeCtx:
    __slots__ = ("_sensor", "_t0")

    def __init__(self, sensor: LatencySensor) -> None:
        self._sensor = sensor
        self._t0 = 0.0

    def __enter__(self) -> "_TimeCtx":
        self._t0 = perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._sensor.record((perf_counter() - self._t0) * 1000.0)
