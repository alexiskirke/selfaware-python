"""Connection sensor: GRIEF on disconnect, LUST on reconnect.

Network/database/whatever connections give us our cleanest mapping for
GRIEF: the affect of separation. A drop is a loss; a reconnection is the
restoration of a bond. CARE rises alongside grief because losing a
connection makes you want to look after the things you still have.
"""

from __future__ import annotations

from typing import Dict, Optional

from ..affects import Affect
from .base import Sensor


class ConnectionSensor(Sensor):
    """Track named connection state transitions and emit affect deltas.

    Use :meth:`up` and :meth:`down` to report state. The sensor remembers
    the previous state per name and only emits on transitions, so polling
    a healthy connection costs nothing emotionally.
    """

    name = "connection"

    def __init__(self) -> None:
        self._state: Dict[str, bool] = {}
        self._dropped: list = []
        self._reconnected: list = []

    def up(self, name: str) -> None:
        prev = self._state.get(name)
        self._state[name] = True
        if prev is False:
            self._reconnected.append(name)

    def down(self, name: str) -> None:
        prev = self._state.get(name)
        self._state[name] = False
        if prev is True or prev is None:
            self._dropped.append(name)

    def read(self) -> Optional[Dict[Affect, float]]:
        if not self._dropped and not self._reconnected:
            return None
        out: Dict[Affect, float] = {}
        if self._dropped:
            out[Affect.GRIEF] = min(0.40, len(self._dropped) * 0.20)
            out[Affect.CARE] = min(0.20, len(self._dropped) * 0.10)
        if self._reconnected:
            out[Affect.LUST] = min(0.30, len(self._reconnected) * 0.15)
            out[Affect.PLAY] = min(0.15, len(self._reconnected) * 0.05)
        self._dropped.clear()
        self._reconnected.clear()
        return out
