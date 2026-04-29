"""RAGE-driven circuit breaker.

A circuit breaker that *opens itself* once the program is sufficiently angry
about a particular goal being blocked. Unlike a normal breaker (which counts
errors over a window), this one looks at the affective consequences of the
errors. That means it will trip not just on repeated explicit failures but
on the slow accumulation of frustration: many small timeouts, contention,
retries — anything that pushes RAGE past the threshold.

Once tripped, the breaker stays open until either:

1. RAGE decays back below ``reset_at`` (the natural cool-down), or
2. ``reset()`` is called explicitly.

This is qualitatively different from an error-counting breaker because it
respects context: a brief surge of timeouts during a deployment will not
trip the breaker unless the *program's overall state* is also dysregulated.
"""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Optional

from ..affects import Affect


class CircuitOpen(Exception):
    """Raised by :meth:`CircuitBreaker.guard` when the breaker is open."""


class CircuitBreaker:
    """A breaker whose state is governed by RAGE rather than raw error count."""

    def __init__(
        self,
        name: str = "circuit",
        *,
        reset_at: float = 0.4,
        cooldown: float = 5.0,
    ) -> None:
        self.name = name
        self.reset_at = reset_at
        self.cooldown = cooldown
        self._open = False
        self._opened_at = 0.0
        self._mind: Optional[Any] = None
        self._lock = threading.Lock()

    @property
    def is_open(self) -> bool:
        if not self._open:
            return False
        # Time-based cooldown: even if RAGE stays high, half-open after cooldown.
        if (time.monotonic() - self._opened_at) > self.cooldown:
            if self._mind is None or self._mind.affects[Affect.RAGE] < self.reset_at:
                self._open = False
                return False
        return self._open

    def trigger(self, mind, affect: Affect, intensity: float) -> None:
        with self._lock:
            self._mind = mind
            self._open = True
            self._opened_at = time.monotonic()

    def reset(self) -> None:
        with self._lock:
            self._open = False

    def guard(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator that short-circuits ``fn`` while the breaker is open."""

        def wrapper(*args, **kwargs):
            if self.is_open:
                raise CircuitOpen(f"circuit '{self.name}' is open")
            return fn(*args, **kwargs)

        wrapper.__wrapped__ = fn  # type: ignore[attr-defined]
        wrapper.__name__ = getattr(fn, "__name__", "wrapper")
        wrapper.__qualname__ = getattr(fn, "__qualname__", "wrapper")
        return wrapper

    @contextmanager
    def block(self) -> Iterator[None]:
        """Context manager equivalent of :meth:`guard`."""
        if self.is_open:
            raise CircuitOpen(f"circuit '{self.name}' is open")
        yield

    def __repr__(self) -> str:
        return f"CircuitBreaker(name={self.name!r}, open={self.is_open})"
