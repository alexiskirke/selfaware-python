"""
selfaware-python: a Pankseppian affective runtime for Python.

Two levels of use are supported:

Level 1 — pure Python, zero external dependencies beyond ``psutil``::

    import selfaware as sa

    mind = sa.Mind()
    mind.attach(sa.sensors.LatencySensor())
    mind.attach(sa.sensors.MemorySensor())
    mind.bind(sa.Affect.RAGE, 0.7, sa.reflexes.CircuitBreaker("payments"))

    with mind.observing():
        do_real_work()

Level 2 — opt in to a tiny local LLM as a narrator (does NOT control execution)::

    mind = sa.Mind(narrator=sa.narrator.OllamaNarrator(model="qwen2.5:0.5b"))
    print(mind.reflect())

The two levels share an identical API; switching the narrator on or off
changes how verbose the program becomes, never whether it works.

Top-level exports:

* :class:`Affect`, :class:`AffectVector`, :class:`Feeling` — the data model
* :class:`Mind`, :func:`default_mind` — the orchestrator
* :class:`Sentient` — the ``__feel__`` mixin
* :func:`resilient` — affect-routed error handling decorator
* :mod:`sensors`, :mod:`reflexes`, :mod:`narrator` — building blocks
* :func:`format_exception`, :func:`install_excepthook` — affective tracebacks
* :class:`AffectProfiler` — emotional cost profiling
"""

from __future__ import annotations

__version__ = "0.1.0"

from . import narrator, reflexes, sensors
from .affects import (
    CROSS_INHIBITION,
    DECAY_PER_SEC,
    RESTING_TONE,
    Affect,
    AffectVector,
    Feeling,
    feelings_of,
    step_dynamics,
)
from .decorators import resilient
from .feel import Sentient
from .mind import Mind, default_mind
from .profiler import AffectProfiler
from .traces import format_exception, install as install_excepthook

# Convenience re-exports so users can write `sa.SEEKING` rather than
# `sa.Affect.SEEKING` if they prefer.
SEEKING = Affect.SEEKING
RAGE = Affect.RAGE
FEAR = Affect.FEAR
LUST = Affect.LUST
CARE = Affect.CARE
GRIEF = Affect.GRIEF
PLAY = Affect.PLAY
SATIETY = Affect.SATIETY


__all__ = [
    "__version__",
    # data model
    "Affect",
    "AffectVector",
    "Feeling",
    "feelings_of",
    "step_dynamics",
    "CROSS_INHIBITION",
    "DECAY_PER_SEC",
    "RESTING_TONE",
    # orchestrator
    "Mind",
    "default_mind",
    # protocol
    "Sentient",
    # decorators
    "resilient",
    # building blocks
    "sensors",
    "reflexes",
    "narrator",
    # observability
    "AffectProfiler",
    "format_exception",
    "install_excepthook",
    # convenience
    "SEEKING",
    "RAGE",
    "FEAR",
    "LUST",
    "CARE",
    "GRIEF",
    "PLAY",
    "SATIETY",
]
