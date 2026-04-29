"""Cache sensor: maps hits/misses onto LUST and SEEKING.

Hits are reward (LUST). Misses are exploration (SEEKING). The ratio of the
two over a window gives the program a sense of "how well it knows its
territory" — high hit rates feel like home, low hit rates feel like
wilderness. This is the original Pankseppian dichotomy in microcosm.
"""

from __future__ import annotations

from typing import Dict, Optional

from ..affects import Affect
from .base import Sensor


class CacheSensor(Sensor):
    """Track cache hit/miss counts and emit affect deltas accordingly.

    Wire it up by calling :meth:`hit` / :meth:`miss` from your cache
    wrapper, or by attaching it to a :class:`functools.lru_cache` and
    polling its ``cache_info`` (use :meth:`from_lru` for that).
    """

    name = "cache"

    def __init__(self) -> None:
        self._hits = 0
        self._misses = 0

    def hit(self, n: int = 1) -> None:
        self._hits += n

    def miss(self, n: int = 1) -> None:
        self._misses += n

    @classmethod
    def from_lru(cls, fn) -> "_LruWatcher":
        """Wrap a ``functools.lru_cache``-decorated function."""
        return _LruWatcher(fn)

    def read(self) -> Optional[Dict[Affect, float]]:
        h, m = self._hits, self._misses
        if h == 0 and m == 0:
            return None
        self._hits = self._misses = 0
        total = h + m
        out: Dict[Affect, float] = {}
        if h:
            ratio = h / total
            out[Affect.LUST] = min(0.20, ratio * 0.20)
            out[Affect.SATIETY] = min(0.10, ratio * 0.05)
        if m:
            ratio = m / total
            out[Affect.SEEKING] = min(0.25, ratio * 0.20)
        return out or None


class _LruWatcher(Sensor):
    """Adapter for ``functools.lru_cache`` instances."""

    name = "cache.lru"

    def __init__(self, fn) -> None:
        self._fn = fn
        info = fn.cache_info()
        self._prev_hits = info.hits
        self._prev_misses = info.misses

    def read(self) -> Optional[Dict[Affect, float]]:
        info = self._fn.cache_info()
        d_hits = info.hits - self._prev_hits
        d_misses = info.misses - self._prev_misses
        self._prev_hits = info.hits
        self._prev_misses = info.misses
        if d_hits == 0 and d_misses == 0:
            return None
        c = CacheSensor()
        c.hit(d_hits)
        c.miss(d_misses)
        return c.read()
