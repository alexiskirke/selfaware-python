"""Sensor protocol shared by the bundled sensors."""

from __future__ import annotations

from typing import Mapping, Optional

from ..affects import Affect


class Sensor:
    """Base class for sensors.

    Subclasses override :meth:`read` to return either ``None`` (no signal)
    or a mapping of :class:`Affect` to a small delta. Per-tick deltas should
    typically live in [-0.3, +0.3]; larger jumps mask the dynamics and make
    the resulting moods feel jittery rather than emotional.
    """

    name: str = "sensor"

    def read(self) -> Optional[Mapping[Affect, float]]:  # pragma: no cover - interface
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
