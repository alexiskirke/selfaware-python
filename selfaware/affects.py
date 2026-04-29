"""
Pankseppian affect model.

Jaak Panksepp identified seven primary affective systems that are conserved
across mammalian brains. Each one is an action-readiness signal: a way of
tilting the organism toward one class of behaviour rather than another.

We map those signals onto runtime phenomena that are common to almost any
running Python program:

    SEEKING  -> exploration, anticipation     -> cache misses, novel paths
    RAGE     -> blocked goals, frustration    -> stalled threads, retries
    FEAR     -> anticipated threat            -> memory pressure, quotas
    LUST     -> reward, goal-fulfilment       -> high-throughput hot paths
    CARE     -> nurture, protection           -> child processes, cleanup
    GRIEF    -> separation, loss              -> dropped connections
    PLAY     -> social engagement, joy        -> healthy concurrency
    SATIETY  -> consolidation, completion     -> work queues drained

This is not a metaphor. The mapping holds because biological affects are
already a *control architecture* for action selection, and a running program
is an organism that selects actions. Implementing the same control surface
in Python gives us reflexes (circuit breakers, defensive modes, memoization)
that are emergent rather than imposed.
"""

from __future__ import annotations

import enum
import math
import time
from dataclasses import dataclass, field
from typing import Dict, Iterable, Iterator, Optional, Tuple


class Affect(enum.Enum):
    """The eight affects this runtime tracks (Panksepp's seven plus SATIETY).

    Members are ordered Pankseppian-first so iteration produces a sensible
    default. SATIETY is non-canonical but pragmatically necessary: programs,
    unlike organisms, frequently *finish* tasks, and the absence of a
    completion signal otherwise leaves SEEKING running forever.
    """

    SEEKING = "seeking"
    RAGE = "rage"
    FEAR = "fear"
    LUST = "lust"
    CARE = "care"
    GRIEF = "grief"
    PLAY = "play"
    SATIETY = "satiety"

    @property
    def valence(self) -> float:
        """Approximate hedonic valence in [-1, 1]; not used for control logic."""
        return _VALENCE[self]

    @property
    def glyph(self) -> str:
        """Single-character symbol for compact pretty-printing."""
        return _GLYPH[self]

    def __str__(self) -> str:
        return self.value


_VALENCE: Dict[Affect, float] = {
    Affect.SEEKING: 0.4,
    Affect.RAGE: -0.7,
    Affect.FEAR: -0.6,
    Affect.LUST: 0.8,
    Affect.CARE: 0.5,
    Affect.GRIEF: -0.8,
    Affect.PLAY: 0.7,
    Affect.SATIETY: 0.6,
}


_GLYPH: Dict[Affect, str] = {
    Affect.SEEKING: "?",
    Affect.RAGE: "!",
    Affect.FEAR: "~",
    Affect.LUST: "*",
    Affect.CARE: "+",
    Affect.GRIEF: ".",
    Affect.PLAY: "^",
    Affect.SATIETY: "=",
}


# Cross-inhibition weights. When affect A is strong it suppresses affect B by
# the listed factor per second. This is the simplest possible analogue of
# the lateral inhibition seen between Pankseppian systems and is what gives
# the runtime its emergent moods rather than seven independent dials.
CROSS_INHIBITION: Dict[Affect, Dict[Affect, float]] = {
    Affect.SEEKING: {Affect.FEAR: 0.4, Affect.SATIETY: 0.3},
    Affect.FEAR:    {Affect.SEEKING: 0.6, Affect.PLAY: 0.5, Affect.LUST: 0.4},
    Affect.RAGE:    {Affect.FEAR: 0.5, Affect.CARE: 0.3, Affect.PLAY: 0.6},
    Affect.LUST:    {Affect.SEEKING: 0.5, Affect.FEAR: 0.2},
    Affect.CARE:    {Affect.RAGE: 0.4},
    Affect.GRIEF:   {Affect.SEEKING: 0.3, Affect.PLAY: 0.7, Affect.LUST: 0.5},
    Affect.PLAY:    {Affect.FEAR: 0.4, Affect.GRIEF: 0.4},
    Affect.SATIETY: {Affect.SEEKING: 0.7, Affect.LUST: 0.2},
}


# Per-second exponential decay constant for each affect. RAGE decays faster
# than GRIEF, mirroring the empirical observation that anger is acute and
# grief is sustained. SEEKING never fully zeroes out: there is always a
# resting curiosity drive.
DECAY_PER_SEC: Dict[Affect, float] = {
    Affect.SEEKING: 0.10,
    Affect.RAGE:    0.40,
    Affect.FEAR:    0.20,
    Affect.LUST:    0.25,
    Affect.CARE:    0.10,
    Affect.GRIEF:   0.05,
    Affect.PLAY:    0.30,
    Affect.SATIETY: 0.50,
}


# Resting tone: the baseline level each affect drifts toward in the absence
# of stimulation. SEEKING's nonzero rest is intentional; an organism with no
# curiosity is dead.
RESTING_TONE: Dict[Affect, float] = {
    Affect.SEEKING: 0.10,
    Affect.RAGE:    0.0,
    Affect.FEAR:    0.0,
    Affect.LUST:    0.0,
    Affect.CARE:    0.05,
    Affect.GRIEF:   0.0,
    Affect.PLAY:    0.05,
    Affect.SATIETY: 0.0,
}


@dataclass
class AffectVector:
    """A point in 8-dimensional affect space.

    All intensities live in [0, 1]. The vector is the runtime's working memory
    of how it currently *feels*; reflexes read it, sensors write to it, and
    cross-inhibition shapes its trajectory.
    """

    intensities: Dict[Affect, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for a in Affect:
            self.intensities.setdefault(a, RESTING_TONE[a])

    def __getitem__(self, key: Affect) -> float:
        return self.intensities[key]

    def __setitem__(self, key: Affect, value: float) -> None:
        self.intensities[key] = _clip(value)

    def __iter__(self) -> Iterator[Tuple[Affect, float]]:
        return iter(self.intensities.items())

    def excite(self, affect: Affect, amount: float) -> None:
        """Drive an affect upward by `amount`, clipped at 1.0.

        Excitation is additive rather than multiplicative because biological
        affects also sum across stimuli; two near-misses are scarier than one.
        """
        self.intensities[affect] = _clip(self.intensities[affect] + amount)

    def soothe(self, affect: Affect, amount: float) -> None:
        """Drive an affect downward by `amount`, clipped at 0.0."""
        self.intensities[affect] = _clip(self.intensities[affect] - amount)

    def dominant(self) -> Tuple[Affect, float]:
        """Return the strongest affect; the program's current mood-leader."""
        return max(self.intensities.items(), key=lambda kv: kv[1])

    def mood(self) -> str:
        """Plain-English summary of the current state.

        We deliberately do not call out to an LLM here: the v0.1 promise is
        that you get a credible mood read with zero external dependencies.
        """
        a, v = self.dominant()
        if v < 0.15:
            return "calm"
        return f"{_MOOD_WORDS[a]} ({v:.0%})"

    def copy(self) -> "AffectVector":
        return AffectVector(intensities=dict(self.intensities))

    def __repr__(self) -> str:
        parts = [f"{a.glyph}{v:.2f}" for a, v in self.intensities.items() if v > 0.05]
        return "AffectVector(" + " ".join(parts) + ")" if parts else "AffectVector(calm)"


_MOOD_WORDS: Dict[Affect, str] = {
    Affect.SEEKING: "curious",
    Affect.RAGE:    "frustrated",
    Affect.FEAR:    "anxious",
    Affect.LUST:    "elated",
    Affect.CARE:    "tender",
    Affect.GRIEF:   "bereft",
    Affect.PLAY:    "playful",
    Affect.SATIETY: "satisfied",
}


def step_dynamics(
    vec: AffectVector,
    dt: float,
    *,
    decay: Dict[Affect, float] = DECAY_PER_SEC,
    inhibition: Dict[Affect, Dict[Affect, float]] = CROSS_INHIBITION,
    resting: Dict[Affect, float] = RESTING_TONE,
) -> AffectVector:
    """Advance the affect vector by `dt` seconds.

    Three forces act on every affect simultaneously:

    1. Exponential decay toward the resting tone. This is what makes a panic
       attack subside even if the threat persists at a constant level.
    2. Cross-inhibition from currently dominant affects. Strong RAGE drains
       FEAR; strong SATIETY drains SEEKING. This is what produces moods
       rather than independent dials.
    3. The resting tone itself, slowly pulling each affect back toward its
       homeostatic floor.

    The integration is forward-Euler with a per-step time constant; for the
    sample rates we care about (50ms-1s) this is indistinguishable from a
    proper ODE solver and an order of magnitude cheaper.
    """
    if dt <= 0:
        return vec
    new = vec.copy()
    for a in Affect:
        target = resting[a]
        decayed = target + (vec[a] - target) * math.exp(-decay[a] * dt)
        new[a] = decayed

    inhibition_drains: Dict[Affect, float] = {a: 0.0 for a in Affect}
    for source, targets in inhibition.items():
        src_strength = vec[source]
        if src_strength <= 0.0:
            continue
        for tgt, weight in targets.items():
            inhibition_drains[tgt] += src_strength * weight * dt

    for a, drain in inhibition_drains.items():
        if drain > 0.0:
            new[a] = max(resting[a], new[a] - drain)

    return new


def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


@dataclass(frozen=True)
class Feeling:
    """An object's self-report of how it is currently doing.

    Returned by ``__feel__`` implementations. We use a dataclass rather than a
    bare tuple so that downstream code can carry forward a free-form ``note``
    that surfaces in stack traces and narrator output.
    """
    affect: Affect
    intensity: float = 0.5
    note: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "intensity", _clip(self.intensity))

    def __repr__(self) -> str:
        n = f" '{self.note}'" if self.note else ""
        return f"Feeling({self.affect.value}={self.intensity:.2f}{n})"


def feelings_of(obj: object) -> Iterable[Feeling]:
    """Ask `obj` how it feels, if it implements the protocol.

    Objects opt in by defining ``__feel__`` returning either a single
    ``Feeling`` or an iterable of them. Anything else (including ``None``)
    yields no feelings. Errors during ``__feel__`` are swallowed: an object
    that crashes while introspecting should not crash the rest of the system.
    """
    feeler = getattr(obj, "__feel__", None)
    if feeler is None:
        return ()
    try:
        result = feeler()
    except Exception:
        return ()
    if result is None:
        return ()
    if isinstance(result, Feeling):
        return (result,)
    if isinstance(result, Affect):
        return (Feeling(result, 0.5),)
    try:
        return tuple(f for f in result if isinstance(f, Feeling))
    except TypeError:
        return ()


def now() -> float:
    """Monotonic clock used everywhere; isolated so tests can monkey-patch."""
    return time.monotonic()
