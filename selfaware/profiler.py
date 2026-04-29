"""
Affect-gradient profiling.

Most profilers measure how long each function takes. This one measures the
*emotional cost* of each function: by how much each Pankseppian affect
changed across its execution. It's a different lens on hot-paths: the
function that costs you 5ms but pushes FEAR up by 0.3 every time it runs is
not actually cheap, because the FEAR will eventually trip a circuit breaker
or a defensive-mode cascade somewhere downstream.

Usage::

    profiler = AffectProfiler(mind)
    with profiler.scope("ingest"):
        ingest_batch()
    print(profiler.report())
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, Iterator, List

from .affects import Affect, AffectVector
from .mind import Mind, default_mind, now


@dataclass
class _ScopeRecord:
    label: str
    calls: int = 0
    duration_ms: float = 0.0
    deltas: Dict[Affect, float] = field(default_factory=lambda: {a: 0.0 for a in Affect})


class AffectProfiler:
    """Aggregate per-scope affect deltas and wall time."""

    def __init__(self, mind: Mind = None) -> None:  # type: ignore[assignment]
        self.mind = mind or default_mind()
        self._scopes: Dict[str, _ScopeRecord] = {}
        self._lock = threading.Lock()

    @contextmanager
    def scope(self, label: str) -> Iterator[None]:
        before = self.mind.affects.copy()
        t0 = now()
        try:
            yield
        finally:
            t1 = now()
            after = self.mind.affects
            with self._lock:
                rec = self._scopes.setdefault(label, _ScopeRecord(label=label))
                rec.calls += 1
                rec.duration_ms += (t1 - t0) * 1000.0
                for a in Affect:
                    rec.deltas[a] += after[a] - before[a]

    def measure(self, fn):
        """Decorator equivalent of :meth:`scope`."""
        label = fn.__qualname__

        def wrapper(*args, **kwargs):
            with self.scope(label):
                return fn(*args, **kwargs)

        wrapper.__wrapped__ = fn  # type: ignore[attr-defined]
        wrapper.__name__ = getattr(fn, "__name__", "wrapper")
        wrapper.__qualname__ = label
        wrapper.__doc__ = fn.__doc__
        return wrapper

    def records(self) -> List[_ScopeRecord]:
        with self._lock:
            return [_clone(r) for r in self._scopes.values()]

    def report(self, *, top: int = 10) -> str:
        records = self.records()
        # Rank by "emotional cost": L1 norm of the delta vector.
        records.sort(key=lambda r: -sum(abs(v) for v in r.deltas.values()))
        records = records[:top]

        lines = []
        lines.append(f"{'scope':<28} {'calls':>6} {'time(ms)':>10}  affect deltas")
        lines.append("-" * 78)
        for r in records:
            sig = ", ".join(
                f"{a.glyph}{r.deltas[a]:+.2f}"
                for a in Affect
                if abs(r.deltas[a]) > 0.05
            ) or "—"
            lines.append(f"{r.label[:28]:<28} {r.calls:>6} {r.duration_ms:>10.1f}  {sig}")
        return "\n".join(lines)


def _clone(r: _ScopeRecord) -> _ScopeRecord:
    new = _ScopeRecord(label=r.label, calls=r.calls, duration_ms=r.duration_ms)
    new.deltas = dict(r.deltas)
    return new
