"""SEEKING-driven speculative memoization.

The runtime's curiosity reflex. When SEEKING is high, the program is in
"explore mode" — calling functions it does not yet have cached results for.
The classical engineering response is to memoize aggressively to amortise
the cost of exploration.

Crucially, the memoizer is *conditional*: it only caches when curiosity is
high enough to justify the memory cost. Once SEEKING decays (the program
has settled into known territory), new entries stop being added and the
cache eventually evicts itself. This is what "speculative" means here: the
cache is an optimistic bet that pays off only while we are exploring.
"""

from __future__ import annotations

import functools
import threading
from collections import OrderedDict
from typing import Any, Callable, Dict, Optional, Tuple

from ..affects import Affect


class SpeculativeMemoizer:
    """A bounded memoization cache that fills only while SEEKING is hot.

    Wrap any pure-ish callable::

        memo = SpeculativeMemoizer(max_size=1024)
        mind.bind(Affect.SEEKING, 0.4, memo)

        @memo.cache
        def parse(line): ...

    While SEEKING is high, ``parse`` calls will be cached. When SEEKING
    cools, the cache stops admitting new entries (existing entries continue
    to serve hits). This means exploration phases pay a memory cost only
    proportional to their actual novelty.
    """

    def __init__(self, max_size: int = 1024) -> None:
        self.max_size = max_size
        self._cache: "OrderedDict[Tuple, Any]" = OrderedDict()
        self._engaged = False
        self._mind: Optional[Any] = None
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._admitted = 0
        self._declined = 0

    @property
    def engaged(self) -> bool:
        return self._engaged

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "hits": self._hits,
            "misses": self._misses,
            "admitted": self._admitted,
            "declined": self._declined,
            "size": len(self._cache),
        }

    def trigger(self, mind, affect: Affect, intensity: float) -> None:
        with self._lock:
            self._engaged = True
            self._mind = mind

    def cool_down(self) -> None:
        with self._lock:
            self._engaged = False

    def _admit(self, key: Tuple, value: Any) -> None:
        if not self._engaged:
            self._declined += 1
            return
        with self._lock:
            self._cache[key] = value
            self._cache.move_to_end(key)
            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)
            self._admitted += 1

    def cache(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        """Decorate ``fn`` so its results are memoized while SEEKING is high."""

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                key = (fn.__qualname__, args, tuple(sorted(kwargs.items())))
            except TypeError:
                # Unhashable args -> bypass cache entirely.
                return fn(*args, **kwargs)
            with self._lock:
                if key in self._cache:
                    self._hits += 1
                    self._cache.move_to_end(key)
                    return self._cache[key]
                self._misses += 1
            value = fn(*args, **kwargs)
            self._admit(key, value)
            return value

        wrapper.cache_info = lambda: self.stats  # type: ignore[attr-defined]
        wrapper.cache_clear = lambda: self._cache.clear()  # type: ignore[attr-defined]
        return wrapper

    def __repr__(self) -> str:
        s = self.stats
        return f"SpeculativeMemoizer(engaged={self._engaged}, size={s['size']}, hits={s['hits']})"
