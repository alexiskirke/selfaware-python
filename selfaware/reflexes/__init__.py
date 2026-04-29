"""
Reflexes: things the runtime *does* when an affect crosses threshold.

A reflex is what separates an affective system from a logging system. The
package's central thesis is that emotions must drive policy, not just
display. Every bundled reflex therefore has a concrete, testable behaviour:

* :class:`CircuitBreaker` — RAGE-driven; trips on repeated frustration.
* :class:`DefensiveMode` — FEAR-driven; shrinks batch sizes and validates more.
* :class:`SpeculativeMemoizer` — SEEKING-driven; caches new code paths.
* :class:`Caretaker` — CARE-driven; ensures graceful child cleanup.

You bind a reflex to an affect+threshold via :meth:`Mind.bind` and the
runtime fires it edge-triggered when the affect rises through the threshold.
"""

from .breaker import CircuitBreaker, CircuitOpen
from .defensive import DefensiveMode
from .seeking import SpeculativeMemoizer
from .caretaker import Caretaker

__all__ = [
    "CircuitBreaker",
    "CircuitOpen",
    "DefensiveMode",
    "SpeculativeMemoizer",
    "Caretaker",
]
