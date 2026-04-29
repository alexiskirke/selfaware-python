"""
Sensors: small, composable observers that turn runtime signals into affect
deltas.

Every sensor implements one method::

    def read(self) -> Mapping[Affect, float] | None

returning a dict of affect-to-delta nudges (positive excites, negative
soothes), or ``None`` if it has nothing to report this tick. The
:class:`~selfaware.mind.Mind` is responsible for actually applying them; a
sensor is just a stateless-ish observer.

Sensors are designed so that *not having one attached is the right default*.
Many of the bundled sensors gracefully degrade when their data sources are
unavailable; for instance :class:`MemorySensor` becomes a no-op if ``psutil``
is missing.
"""

from .base import Sensor
from .latency import LatencySensor
from .memory import MemorySensor
from .errors import ErrorSensor
from .cache import CacheSensor
from .novelty import NoveltySensor
from .connection import ConnectionSensor

__all__ = [
    "Sensor",
    "LatencySensor",
    "MemorySensor",
    "ErrorSensor",
    "CacheSensor",
    "NoveltySensor",
    "ConnectionSensor",
]
