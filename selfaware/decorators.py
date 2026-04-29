"""
Decorators for affect-aware control flow.

The headline is :func:`resilient`, which wraps a callable so that exceptions
are routed through the affective state. The handler chosen depends not just
on the exception type but on what the program is *feeling* at that moment.
This is the same separation of concerns that biological organisms use:
the same stimulus produces different reactions depending on internal state.
"""

from __future__ import annotations

import functools
import time
from typing import Any, Callable, Dict, Optional, Union

from .affects import Affect
from .mind import Mind, default_mind
from .sensors.errors import classify


Strategy = Union[str, Callable[..., Any]]


_DEFAULT_STRATEGIES: Dict[Affect, str] = {
    Affect.FEAR: "retry_cautiously",
    Affect.RAGE: "change_strategy",
    Affect.GRIEF: "reconnect",
    Affect.SEEKING: "investigate",
    Affect.CARE: "cleanup",
}


def resilient(
    fn: Optional[Callable[..., Any]] = None,
    *,
    on_error: Optional[Dict[Affect, Strategy]] = None,
    fallback: Optional[Callable[..., Any]] = None,
    mind: Optional[Mind] = None,
    max_retries: int = 3,
    backoff: float = 0.1,
):
    """Wrap ``fn`` with affect-routed error handling.

    Each exception is:

    1. classified by the bundled ``classify()`` (RAGE/FEAR/GRIEF/SEEKING/CARE),
    2. used to excite the attached :class:`Mind`,
    3. routed to a strategy keyed off the current dominant affect.

    Strategies may be either a string name (resolved against built-ins) or
    a callable taking ``(fn, args, kwargs, exc, attempt)``. Built-in strategy
    names:

    * ``"retry_cautiously"`` — exponential backoff, full retry budget.
    * ``"change_strategy"`` — break out of the retry loop and call ``fallback``.
    * ``"reconnect"`` — single retry after a short sleep; suitable for
      transient I/O.
    * ``"investigate"`` — log/raise immediately; we do not understand the error.
    * ``"cleanup"`` — fire any registered ``Caretaker`` and re-raise.
    """

    def _decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
        m = mind or default_mind()
        routes = dict(_DEFAULT_STRATEGIES)
        if on_error:
            routes.update(on_error)

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            attempt = 0
            last_exc: Optional[BaseException] = None
            while True:
                attempt += 1
                try:
                    return fn(*args, **kwargs)
                except BaseException as exc:  # noqa: BLE001 — we route everything
                    last_exc = exc
                    a, mag = classify(exc)
                    m.excite(a, mag, note=f"{type(exc).__name__} in {fn.__qualname__}")

                    dom_affect, dom_intensity = m.affects.dominant()
                    strategy = routes.get(dom_affect) or routes.get(a) or "investigate"
                    action = _resolve(strategy)
                    decision = action(fn, args, kwargs, exc, attempt, m)

                    if decision == "retry":
                        if attempt >= max_retries:
                            if fallback is not None:
                                return fallback(*args, **kwargs)
                            raise
                        time.sleep(backoff * (2 ** (attempt - 1)))
                        continue
                    if decision == "fallback":
                        if fallback is not None:
                            return fallback(*args, **kwargs)
                        raise
                    raise

        return wrapper

    if fn is not None:
        return _decorate(fn)
    return _decorate


# ---------------------------------------------------------------------------
# Built-in strategies
# ---------------------------------------------------------------------------

def _retry_cautiously(fn, args, kwargs, exc, attempt, mind) -> str:
    return "retry"


def _change_strategy(fn, args, kwargs, exc, attempt, mind) -> str:
    return "fallback"


def _reconnect(fn, args, kwargs, exc, attempt, mind) -> str:
    if attempt >= 2:
        return "fallback"
    time.sleep(0.05)
    return "retry"


def _investigate(fn, args, kwargs, exc, attempt, mind) -> str:
    # No retry: re-raise so the developer sees the unfamiliar exception.
    return "raise"


def _cleanup(fn, args, kwargs, exc, attempt, mind) -> str:
    # Force-trigger CARE; this lets a registered Caretaker do its work even
    # though the threshold technically may not have crossed.
    mind.excite(Affect.CARE, 0.6, note=f"forced cleanup after {type(exc).__name__}")
    mind.tick()
    return "raise"


_BUILTINS: Dict[str, Callable] = {
    "retry_cautiously": _retry_cautiously,
    "change_strategy": _change_strategy,
    "reconnect": _reconnect,
    "investigate": _investigate,
    "cleanup": _cleanup,
}


def _resolve(strategy: Strategy) -> Callable:
    if callable(strategy):
        return strategy  # type: ignore[return-value]
    try:
        return _BUILTINS[strategy]  # type: ignore[index]
    except KeyError as exc:
        raise ValueError(f"unknown strategy: {strategy!r}") from exc
