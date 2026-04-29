"""CARE-driven graceful shutdown.

CARE in Panksepp's model is the affect that organises nurturing, protection,
and parental behaviour. Its software analogue is the cleanup obligation: the
need to look after child processes, open file handles, network connections,
and other resources that depend on the parent for survival.

The :class:`Caretaker` reflex registers cleanup callables and runs them in
a deterministic order when CARE crosses threshold (typically because of
memory pressure, an interrupt signal, or repeated GRIEF from disconnected
peers). Unlike ``atexit``, it can fire *during* a session rather than only
on interpreter teardown, making it useful for long-running services that
need to gracefully shed load.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

from ..affects import Affect


@dataclass(order=True)
class _Charge:
    priority: int
    name: str = field(compare=False)
    fn: Callable[[], None] = field(compare=False)


class Caretaker:
    """Registry of cleanup callables that fire when CARE peaks.

    Higher-priority charges run first, mirroring the biological observation
    that under acute caretaking pressure organisms triage: dependent young
    first, then conspecifics, then territory.
    """

    def __init__(self, name: str = "caretaker") -> None:
        self.name = name
        self._charges: List[_Charge] = []
        self._lock = threading.Lock()
        self._fired = False

    @property
    def fired(self) -> bool:
        return self._fired

    def adopt(self, fn: Callable[[], None], *, name: Optional[str] = None, priority: int = 0) -> None:
        """Register a cleanup callable.

        ``priority`` is sorted descending; charges with the same priority
        run in registration order.
        """
        with self._lock:
            self._charges.append(_Charge(priority=-priority, name=name or fn.__qualname__, fn=fn))
            self._charges.sort()

    def trigger(self, mind, affect: Affect, intensity: float) -> None:
        with self._lock:
            charges = list(self._charges)
            self._fired = True
        for c in charges:
            try:
                c.fn()
            except Exception:
                # Caretaking that fails on one charge should not abandon the rest.
                continue

    def reset(self) -> None:
        with self._lock:
            self._fired = False

    def __repr__(self) -> str:
        return f"Caretaker(charges={len(self._charges)}, fired={self._fired})"
