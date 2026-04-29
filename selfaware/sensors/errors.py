"""Error sensor: classifies exceptions onto Pankseppian affects.

Different exception classes mean very different things to a running program,
and the affective system lets us treat them differently:

* Connection failures, timeouts, I/O errors -> RAGE (blocked goals).
  Repeated ConnectionRefused is the canonical RAGE-trigger; the goal is
  reachable in principle but something is in the way.
* Resource errors (MemoryError, OSError ENOMEM) -> FEAR. Existential.
* Lookup failures (KeyError, FileNotFoundError) -> GRIEF on the *first*
  occurrence; they are an absence, not an obstruction. They become RAGE
  when they recur because then they are an obstruction.
* Parse / type errors -> SEEKING. We need to learn something to proceed.
* Anything subclassing ``KeyboardInterrupt`` or ``SystemExit`` -> CARE,
  to elevate cleanup as a goal.
"""

from __future__ import annotations

from collections import Counter, deque
from typing import Deque, Dict, Optional, Tuple, Type

from ..affects import Affect
from .base import Sensor


_CLASSIFIERS: Tuple[Tuple[Tuple[Type[BaseException], ...], Affect, float], ...] = (
    ((ConnectionError, TimeoutError, BrokenPipeError), Affect.RAGE, 0.15),
    ((MemoryError,), Affect.FEAR, 0.40),
    ((KeyboardInterrupt, SystemExit), Affect.CARE, 0.25),
    ((TypeError, ValueError, SyntaxError), Affect.SEEKING, 0.10),
    ((LookupError, FileNotFoundError, AttributeError), Affect.GRIEF, 0.10),
)


def classify(exc: BaseException) -> Tuple[Affect, float]:
    """Return the (affect, magnitude) excitation for an exception.

    Defaults to ``(SEEKING, 0.05)`` for unknown types: an unfamiliar error
    is, by definition, something we do not yet understand and so should
    investigate. This is the most Pankseppian default we can pick.
    """
    for classes, affect, mag in _CLASSIFIERS:
        if isinstance(exc, classes):
            return affect, mag
    return Affect.SEEKING, 0.05


class ErrorSensor(Sensor):
    """Aggregate exceptions over a sliding window and emit affect deltas.

    The non-obvious behaviour: repeated exceptions of the same type
    *escalate* rather than just sum. Three ``ConnectionRefused`` in a row
    is qualitatively worse than one — it means something systemic is wrong
    — and the sensor expresses that by adding a RAGE bonus that scales with
    repetition.
    """

    name = "errors"

    def __init__(self, *, window: int = 32) -> None:
        self._buf: Deque[BaseException] = deque(maxlen=window)

    def record(self, exc: BaseException) -> None:
        self._buf.append(exc)

    def read(self) -> Optional[Dict[Affect, float]]:
        if not self._buf:
            return None
        items = list(self._buf)
        self._buf.clear()
        out: Dict[Affect, float] = {}
        # By type: tally repetitions to escalate
        counts: Counter = Counter(type(e) for e in items)
        for exc in items:
            a, mag = classify(exc)
            out[a] = out.get(a, 0.0) + mag
        for cls, n in counts.items():
            if n >= 3 and issubclass(cls, (ConnectionError, TimeoutError)):
                # Sustained connection failures escalate from RAGE into FEAR
                # too: "something is wrong with the world".
                bonus = min(0.20, 0.05 * (n - 2))
                out[Affect.RAGE] = out.get(Affect.RAGE, 0.0) + bonus
                out[Affect.FEAR] = out.get(Affect.FEAR, 0.0) + bonus * 0.5
        # Clip per-affect to keep things sane
        return {a: min(0.5, v) for a, v in out.items()} or None
