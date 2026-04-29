"""
The Mind: a thread-safe orchestrator that holds an AffectVector, polls
sensors, runs cross-inhibition dynamics, and dispatches reflexes.

Design choices worth knowing:

- **Explicit instantiation, no magic singletons.** ``Mind()`` is a regular
  Python object; you pass it where you need it. There is, however, a
  ``default_mind()`` for the common case where one process == one program.
- **Pull, not push.** Sensors are polled on tick. This keeps the runtime
  predictable; we do not start background threads unless ``run_in_background``
  is called. A program that imports selfaware should not magically start
  doing things.
- **Reflexes fire on threshold crossings.** A reflex bound to FEAR > 0.7
  fires once when intensity rises through 0.7, not every tick the value
  exceeds it. This is the same edge-triggered semantics as a hardware
  interrupt and matches how biological action thresholds work.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from .affects import (
    Affect,
    AffectVector,
    Feeling,
    feelings_of,
    now,
    step_dynamics,
)


ReflexFn = Callable[["Mind", Affect, float], None]


@dataclass
class _Sensor:
    """Internal record for an attached sensor."""
    name: str
    fn: Callable[[], Any]
    interval: float = 0.0
    last_run: float = 0.0


@dataclass
class _Reflex:
    """Internal record for an edge-triggered reflex.

    ``fired`` tracks hysteresis: a reflex with threshold T fires when the
    affect rises through T and may only fire again after dropping back below
    ``T - hysteresis``. Without this we would get reflex storms whenever the
    intensity hovered near the threshold.
    """
    name: str
    affect: Affect
    threshold: float
    fn: ReflexFn
    hysteresis: float = 0.1
    fired: bool = False


@dataclass
class _LogEntry:
    t: float
    label: str
    delta: Dict[Affect, float] = field(default_factory=dict)
    note: str = ""


class Mind:
    """A self-aware Python runtime.

    The Mind is conceptually one object that:

    * keeps an :class:`AffectVector` describing how the program currently feels,
    * polls attached sensors to update that vector,
    * runs cross-inhibition / decay dynamics every tick,
    * dispatches reflexes when affects cross thresholds,
    * remembers a bounded history of significant changes for stack-trace
      annotation and narration.

    Typical use::

        from selfaware import Mind, sensors, reflexes, Affect

        mind = Mind()
        mind.attach(sensors.LatencySensor())
        mind.attach(sensors.MemorySensor())
        mind.bind(Affect.RAGE, 0.7, reflexes.CircuitBreaker("payments"))

        with mind.observing():
            do_real_work()
    """

    def __init__(
        self,
        *,
        name: str = "mind",
        history: int = 256,
        narrator: Optional["Narrator"] = None,  # type: ignore[name-defined]
    ) -> None:
        self.name = name
        self.affects = AffectVector()
        self._sensors: List[_Sensor] = []
        self._reflexes: List[_Reflex] = []
        self._lock = threading.RLock()
        self._last_tick = now()
        self._history: List[_LogEntry] = []
        self._history_max = history
        self._bg_thread: Optional[threading.Thread] = None
        self._bg_stop = threading.Event()
        self._narrator = narrator

    # ------------------------------------------------------------------
    # Wiring
    # ------------------------------------------------------------------

    def attach(self, sensor: Any, *, name: Optional[str] = None, interval: float = 0.0) -> None:
        """Attach a sensor.

        A sensor is anything callable that returns either ``None`` or a dict
        ``{Affect: delta}`` describing how it wants to nudge the affect
        vector this tick. Sensor objects with a ``read`` method are wrapped
        automatically; that is the convention used by the bundled sensors
        in :mod:`selfaware.sensors`.
        """
        fn = sensor.read if hasattr(sensor, "read") else sensor
        n = name or getattr(sensor, "name", None) or fn.__qualname__
        with self._lock:
            self._sensors.append(_Sensor(name=n, fn=fn, interval=interval))

    def bind(
        self,
        affect: Affect,
        threshold: float,
        reflex: Any,
        *,
        name: Optional[str] = None,
        hysteresis: float = 0.1,
    ) -> None:
        """Bind a reflex to fire when ``affect`` rises through ``threshold``.

        ``reflex`` may be:

        * a plain callable ``f(mind, affect, intensity)`` — direct reflex
        * a callable ``f()`` — wrapped to ignore arguments
        * an object with a ``trigger`` method — bundled-reflex protocol
        """
        if hasattr(reflex, "trigger"):
            fn = lambda m, a, v, _r=reflex: _r.trigger(m, a, v)
            n = name or getattr(reflex, "name", reflex.__class__.__name__)
        else:
            try:
                # accept zero-arg callables for ergonomics
                arity = reflex.__code__.co_argcount  # type: ignore[attr-defined]
            except AttributeError:
                arity = 3
            if arity == 0:
                fn = lambda m, a, v, _r=reflex: _r()
            else:
                fn = reflex
            n = name or getattr(reflex, "__qualname__", "reflex")
        with self._lock:
            self._reflexes.append(
                _Reflex(name=n, affect=affect, threshold=threshold, fn=fn, hysteresis=hysteresis)
            )

    # ------------------------------------------------------------------
    # Direct excitation API (for objects implementing __feel__ etc.)
    # ------------------------------------------------------------------

    def feel(self, source: Any, *, weight: float = 1.0) -> None:
        """Fold an object's :class:`Feeling` reports into the affect vector."""
        for f in feelings_of(source):
            self.excite(f.affect, f.intensity * weight, note=f.note or repr(source))

    def excite(self, affect: Affect, amount: float, *, note: str = "") -> None:
        """Push an affect upward and log it as a notable event."""
        with self._lock:
            before = self.affects[affect]
            self.affects.excite(affect, amount)
            after = self.affects[affect]
            if abs(after - before) > 1e-3:
                self._record(label="excite", delta={affect: after - before}, note=note)

    def soothe(self, affect: Affect, amount: float, *, note: str = "") -> None:
        with self._lock:
            before = self.affects[affect]
            self.affects.soothe(affect, amount)
            after = self.affects[affect]
            if abs(after - before) > 1e-3:
                self._record(label="soothe", delta={affect: after - before}, note=note)

    # ------------------------------------------------------------------
    # The tick
    # ------------------------------------------------------------------

    def tick(self) -> AffectVector:
        """Advance time, poll sensors, apply dynamics, fire reflexes.

        Safe to call from any thread; safe to call from inside a reflex
        (the lock is reentrant, and we snapshot the reflex list before
        dispatch so a reflex can ``mind.bind`` more reflexes without
        invalidating iteration).
        """
        with self._lock:
            t = now()
            dt = max(0.0, t - self._last_tick)
            self._last_tick = t

            for s in self._sensors:
                if s.interval and (t - s.last_run) < s.interval:
                    continue
                s.last_run = t
                try:
                    delta = s.fn()
                except Exception as exc:  # pragma: no cover - sensor crashes
                    self._record(label="sensor-error", note=f"{s.name}: {exc!r}")
                    continue
                if not delta:
                    continue
                changes: Dict[Affect, float] = {}
                for affect, d in delta.items():
                    before = self.affects[affect]
                    if d >= 0:
                        self.affects.excite(affect, d)
                    else:
                        self.affects.soothe(affect, -d)
                    after = self.affects[affect]
                    if abs(after - before) > 1e-3:
                        changes[affect] = after - before
                if changes:
                    self._record(label=f"sensor:{s.name}", delta=changes)

            self.affects = step_dynamics(self.affects, dt)

            self._dispatch_reflexes()

        return self.affects.copy()

    def _dispatch_reflexes(self) -> None:
        snapshot = list(self._reflexes)
        for r in snapshot:
            v = self.affects[r.affect]
            if not r.fired and v >= r.threshold:
                r.fired = True
                self._record(label=f"reflex:{r.name}", note=f"{r.affect.value} {v:.2f} >= {r.threshold:.2f}")
                try:
                    r.fn(self, r.affect, v)
                except Exception as exc:  # pragma: no cover - reflex crashes
                    self._record(label="reflex-error", note=f"{r.name}: {exc!r}")
            elif r.fired and v < (r.threshold - r.hysteresis):
                r.fired = False

    # ------------------------------------------------------------------
    # Background loop (opt-in)
    # ------------------------------------------------------------------

    def run_in_background(self, period: float = 0.25) -> None:
        """Start a daemon thread that calls :meth:`tick` every ``period`` s.

        We call this opt-in rather than implicit because importing a library
        should never cause it to spin up threads behind your back. If you
        want push-style emotional updates, you ask for them.
        """
        with self._lock:
            if self._bg_thread is not None:
                return
            self._bg_stop.clear()
            t = threading.Thread(target=self._bg_loop, args=(period,), daemon=True, name=f"{self.name}-tick")
            self._bg_thread = t
            t.start()

    def stop(self) -> None:
        with self._lock:
            self._bg_stop.set()
            t = self._bg_thread
            self._bg_thread = None
        if t is not None:
            t.join(timeout=1.0)

    def _bg_loop(self, period: float) -> None:
        while not self._bg_stop.wait(period):
            try:
                self.tick()
            except Exception:  # pragma: no cover
                pass

    @contextmanager
    def observing(self, *, period: float = 0.25) -> Iterator["Mind"]:
        """Context manager: tick in the background for the duration of a block."""
        self.run_in_background(period=period)
        try:
            yield self
        finally:
            self.stop()

    # ------------------------------------------------------------------
    # History / introspection
    # ------------------------------------------------------------------

    def _record(self, *, label: str, delta: Optional[Dict[Affect, float]] = None, note: str = "") -> None:
        entry = _LogEntry(t=now(), label=label, delta=dict(delta or {}), note=note)
        self._history.append(entry)
        if len(self._history) > self._history_max:
            del self._history[: len(self._history) - self._history_max]

    def history(self, last: Optional[int] = None) -> List[_LogEntry]:
        with self._lock:
            return list(self._history[-last:] if last else self._history)

    def trajectory(self, last: int = 10) -> List[Tuple[Affect, float]]:
        """Return the per-affect cumulative delta over the last `n` events.

        This is what powers affective stack traces: "in the last second the
        program got +0.42 more afraid and +0.18 more enraged."
        """
        recent = self.history(last)
        agg: Dict[Affect, float] = {a: 0.0 for a in Affect}
        for e in recent:
            for a, d in e.delta.items():
                agg[a] += d
        return [(a, v) for a, v in sorted(agg.items(), key=lambda kv: -abs(kv[1])) if abs(v) > 1e-3]

    def mood(self) -> str:
        return self.affects.mood()

    def __repr__(self) -> str:
        a, v = self.affects.dominant()
        return f"Mind(name={self.name!r}, mood={self.mood()!r}, dominant={a.value}={v:.2f})"

    # ------------------------------------------------------------------
    # Narrator (optional LLM)
    # ------------------------------------------------------------------

    def reflect(self, prompt: Optional[str] = None) -> str:
        """Ask the attached narrator (if any) for a plain-English reflection.

        Without a narrator this still produces a useful description by
        falling back to deterministic, dependency-free templating. The point
        is that ``mind.reflect()`` always returns something readable.
        """
        if self._narrator is not None:
            try:
                return self._narrator.narrate(self, prompt=prompt)
            except Exception as exc:  # pragma: no cover - narrator failures
                return f"[narrator unavailable: {exc!r}]\n" + self._fallback_reflection()
        return self._fallback_reflection()

    def _fallback_reflection(self) -> str:
        a, v = self.affects.dominant()
        traj = self.trajectory(last=20)
        traj_str = ", ".join(f"{aa.value} {dd:+.2f}" for aa, dd in traj[:3]) or "none"
        return f"I am {self.affects.mood()}. Lately: {traj_str}."


# ---------------------------------------------------------------------------
# Process-default mind
# ---------------------------------------------------------------------------

_default_mind: Optional[Mind] = None
_default_lock = threading.Lock()


def default_mind() -> Mind:
    """Return the lazily-created process-wide default Mind.

    Most users will be fine with this. Power users wiring up multiple
    independent emotional contexts (e.g. one per worker subprocess) should
    instantiate :class:`Mind` directly.
    """
    global _default_mind
    if _default_mind is None:
        with _default_lock:
            if _default_mind is None:
                _default_mind = Mind(name="default")
    return _default_mind
