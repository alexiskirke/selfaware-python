"""Novelty sensor: drives SEEKING when unfamiliar code paths execute.

We approximate "novelty" as: a tag (typically the qualified name of a
function or call site) that has not been seen in the current window. Each
new tag bumps SEEKING; a stream of *only* familiar tags soothes SEEKING and
nudges SATIETY upward, the way an organism in a known territory relaxes.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, Dict, Optional, Set

from ..affects import Affect
from .base import Sensor


class NoveltySensor(Sensor):
    """Track which tags have been seen recently.

    Most usefully driven by a decorator at the call site::

        novelty = NoveltySensor()

        @novelty.observe
        def parse_record(line): ...

    or manually with :meth:`mark`.
    """

    name = "novelty"

    def __init__(self, *, memory: int = 256) -> None:
        self._seen: Set[str] = set()
        self._order: Deque[str] = deque(maxlen=memory)
        self._novel = 0
        self._familiar = 0

    def mark(self, tag: str) -> bool:
        """Record a tag occurrence; return True iff it was novel."""
        novel = tag not in self._seen
        if novel:
            self._novel += 1
            self._seen.add(tag)
            if len(self._order) == self._order.maxlen:
                evicted = self._order[0]
                # The eviction may or may not match what's in `_seen`; we accept
                # the small leak for simplicity.
                self._seen.discard(evicted)
            self._order.append(tag)
        else:
            self._familiar += 1
        return novel

    def observe(self, fn):
        """Decorator that marks each call to `fn` with its qualified name."""
        tag = getattr(fn, "__qualname__", repr(fn))

        def wrapper(*args, **kwargs):
            self.mark(tag)
            return fn(*args, **kwargs)

        wrapper.__wrapped__ = fn  # type: ignore[attr-defined]
        wrapper.__name__ = getattr(fn, "__name__", "wrapper")
        wrapper.__qualname__ = tag
        wrapper.__doc__ = fn.__doc__
        return wrapper

    def read(self) -> Optional[Dict[Affect, float]]:
        n, f = self._novel, self._familiar
        if n == 0 and f == 0:
            return None
        self._novel = self._familiar = 0
        out: Dict[Affect, float] = {}
        if n:
            out[Affect.SEEKING] = min(0.25, n * 0.05)
        if f and not n:
            out[Affect.SATIETY] = 0.05
        return out or None
