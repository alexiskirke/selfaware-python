"""
Affective stack traces.

A normal stack trace tells you *where* an error occurred. An affective
stack trace also tells you *how the program felt on the way there*: which
affects rose, which dominated at the moment of failure, and what the runtime
suspects about the kind of thing that just happened.

This is the file that contains the screenshot you would put on the README.

Two integration points:

* :func:`format_exception` — explicit, return a string for any exception.
* :func:`install` — replace ``sys.excepthook`` so unhandled exceptions are
  printed in affective form by default.
"""

from __future__ import annotations

import sys
import traceback
from typing import Optional

from .affects import Affect
from .mind import Mind, default_mind
from .sensors.errors import classify


_RESET = "\033[0m"
_DIM = "\033[2m"
_BOLD = "\033[1m"
_COLOURS = {
    Affect.SEEKING: "\033[36m",  # cyan
    Affect.RAGE:    "\033[31m",  # red
    Affect.FEAR:    "\033[35m",  # magenta
    Affect.LUST:    "\033[33m",  # yellow
    Affect.CARE:    "\033[32m",  # green
    Affect.GRIEF:   "\033[34m",  # blue
    Affect.PLAY:    "\033[92m",  # bright green
    Affect.SATIETY: "\033[90m",  # bright black
}


def format_exception(
    exc: BaseException,
    *,
    mind: Optional[Mind] = None,
    colour: Optional[bool] = None,
) -> str:
    """Render ``exc`` as an affective stack trace.

    The output is a normal Python traceback followed by an "affective
    epilogue" describing the dominant emotion, recent trajectory, and a
    plain-English suggestion of what the runtime thinks just happened.
    """
    m = mind or default_mind()
    a, mag = classify(exc)
    m.excite(a, mag, note=f"{type(exc).__name__}")

    use_colour = sys.stderr.isatty() if colour is None else colour
    c = (lambda code, s: f"{code}{s}{_RESET}") if use_colour else (lambda _c, s: s)

    body = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    body = body.rstrip()

    dominant, intensity = m.affects.dominant()
    traj = m.trajectory(last=20)

    suggestion = _suggest(exc, dominant, intensity)

    lines = [body, ""]
    lines.append(c(_BOLD, "Affective trace") + c(_DIM, "  (selfaware-python)"))
    lines.append(c(_DIM, "  while this exception was thrown the program felt:"))
    lines.append("    " + c(_COLOURS[dominant], f"{dominant.value:<8} {intensity:>5.2f}") + c(_DIM, "  <-- dominant"))
    for affect, value in m.affects.intensities.items():
        if affect == dominant or value < 0.1:
            continue
        lines.append("    " + c(_COLOURS[affect], f"{affect.value:<8} {value:>5.2f}"))
    if traj:
        lines.append("")
        lines.append(c(_DIM, "  trajectory (last 20 events):"))
        for affect, delta in traj[:5]:
            arrow = "+" if delta > 0 else ""
            lines.append("    " + c(_COLOURS[affect], f"{affect.value:<8} {arrow}{delta:.2f}"))

    lines.append("")
    lines.append(c(_BOLD, "  reflection: ") + suggestion)
    return "\n".join(lines)


def _suggest(exc: BaseException, dominant: Affect, intensity: float) -> str:
    """Heuristic plain-English suggestion based on type + dominant affect."""
    name = type(exc).__name__
    if isinstance(exc, (ConnectionError, TimeoutError)):
        if dominant == Affect.RAGE and intensity > 0.5:
            return (
                f"{name} arrived while I was already frustrated. Something is "
                "systemically blocking us; consider opening a circuit breaker "
                "or backing off rather than retrying."
            )
        return f"{name} looks like a transient network issue; retrying with backoff is reasonable."
    if isinstance(exc, MemoryError):
        return (
            "I'm out of memory. Shrink batch sizes, free large objects, "
            "or shed load before continuing."
        )
    if isinstance(exc, (KeyError, AttributeError, FileNotFoundError)):
        if dominant == Affect.GRIEF:
            return f"{name} is the third absence in a row; the resource I expected is gone, not late."
        return f"{name} suggests a missing key or attribute — check upstream contract."
    if isinstance(exc, (TypeError, ValueError)):
        return f"{name} suggests an unfamiliar input shape; investigate before retrying."
    if dominant == Affect.FEAR and intensity >= 0.45:
        return (
            f"{name} happened while the runtime was already anxious — there is "
            "likely an upstream stressor (memory, quotas, latency) worth checking."
        )
    if dominant == Affect.RAGE and intensity >= 0.45:
        return (
            f"{name} happened while the runtime was already frustrated — recent "
            "errors suggest something upstream is blocking goals; consider "
            "easing off retries before this one."
        )
    return f"{name} occurred. I have no strong intuition; logging and re-raising."


def install(mind: Optional[Mind] = None) -> None:
    """Install an affective ``sys.excepthook``.

    Calling this once at startup turns every unhandled exception into an
    affective stack trace. Idempotent; calling twice does nothing extra.
    """
    m = mind or default_mind()
    if getattr(sys.excepthook, "_selfaware_installed", False):
        return

    def hook(exc_type, exc, tb):
        sys.stderr.write(format_exception(exc, mind=m))
        sys.stderr.write("\n")

    hook._selfaware_installed = True  # type: ignore[attr-defined]
    sys.excepthook = hook
