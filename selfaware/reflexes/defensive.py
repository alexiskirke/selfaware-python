"""FEAR-driven defensive mode.

When the program is afraid (memory pressure, repeated unfamiliar errors,
escalating timeouts), it should fight less and verify more. ``DefensiveMode``
publishes a small set of *posture knobs* that other code can read to adjust
its behaviour without having to know anything about Pankseppian affects:

* ``batch_size``: shrinks under FEAR. Smaller batches limit the blast
  radius of a failure and free memory faster.
* ``validate``: a boolean that flips to ``True`` while afraid, asking
  surrounding code to perform extra checks it would normally skip.
* ``parallelism``: a hint for how many concurrent workers to use.

The reflex does not patch your code. It just publishes the knob values; you
read them where it matters. This keeps the affective system orthogonal to
your business logic.
"""

from __future__ import annotations

import threading
from typing import Any

from ..affects import Affect


class DefensiveMode:
    """A small bag of posture knobs that respond to FEAR.

    Typical use::

        defensive = DefensiveMode(default_batch_size=100)
        mind.bind(Affect.FEAR, 0.5, defensive)
        ...
        for chunk in batched(items, defensive.batch_size):
            if defensive.validate:
                check_invariants(chunk)
            process(chunk)
    """

    def __init__(
        self,
        *,
        default_batch_size: int = 100,
        min_batch_size: int = 10,
        default_parallelism: int = 8,
        min_parallelism: int = 1,
    ) -> None:
        self._default_batch = default_batch_size
        self._min_batch = min_batch_size
        self._default_par = default_parallelism
        self._min_par = min_parallelism
        self._lock = threading.Lock()
        self._engaged = False
        self._fear = 0.0

    @property
    def engaged(self) -> bool:
        return self._engaged

    @property
    def batch_size(self) -> int:
        if not self._engaged:
            return self._default_batch
        # Lerp from default down to min as fear rises from threshold to 1.0.
        # We use the latest known fear (set on trigger). It will decay
        # naturally and the next trigger will bring this back up.
        ratio = max(0.0, min(1.0, self._fear))
        size = self._default_batch + (self._min_batch - self._default_batch) * ratio
        return max(self._min_batch, int(size))

    @property
    def parallelism(self) -> int:
        if not self._engaged:
            return self._default_par
        ratio = max(0.0, min(1.0, self._fear))
        p = self._default_par + (self._min_par - self._default_par) * ratio
        return max(self._min_par, int(p))

    @property
    def validate(self) -> bool:
        return self._engaged

    def trigger(self, mind, affect: Affect, intensity: float) -> None:
        with self._lock:
            self._engaged = True
            self._fear = intensity
        # Reflex hysteresis is handled by the Mind, but we also want the
        # *level* to update continuously while engaged, so we register a
        # lightweight tick listener via a sensor-shaped callback.
        # For simplicity, just refresh on every trigger; for finer-grained
        # tracking use mind.affects[Affect.FEAR] directly.

    def relax(self) -> None:
        with self._lock:
            self._engaged = False
            self._fear = 0.0

    def update_from(self, mind) -> None:
        """Optional: pull current FEAR intensity from a mind to refresh knobs.

        Useful if you want batch_size to track the *current* fear level
        rather than the level at which the reflex first fired.
        """
        with self._lock:
            self._fear = mind.affects[Affect.FEAR]
            self._engaged = self._fear > 1e-3

    def __repr__(self) -> str:
        return (
            f"DefensiveMode(engaged={self._engaged}, "
            f"batch_size={self.batch_size}, parallelism={self.parallelism})"
        )
