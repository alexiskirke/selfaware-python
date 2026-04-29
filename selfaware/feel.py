"""
The ``__feel__`` protocol and the ``Sentient`` mixin.

Python's expressive power comes largely from its protocol system: ``__iter__``,
``__enter__``, ``__repr__``, and friends. ``selfaware-python`` adds one more:
``__feel__``, which any object can implement to report its current affective
state.

A class that participates in the protocol can be passed to ``mind.feel(obj)``
and have its self-report folded into the runtime's affect vector. The
:class:`Sentient` mixin provides a turnkey implementation: subclass it,
override :meth:`Sentient.__feel__` (or one of the convenience hooks), and
your object will also gain a mood-aware ``__repr__`` that surfaces its
current emotion when printed in the REPL.
"""

from __future__ import annotations

from typing import Iterable, Optional, Union

from .affects import Affect, Feeling, feelings_of


FeelReport = Union[None, Affect, Feeling, Iterable[Feeling]]


class Sentient:
    """Mixin that gives a class a mood-aware ``__repr__`` and a clean hook
    for implementing ``__feel__``.

    Override either:

    * :meth:`__feel__` directly (returning a Feeling, an Affect, or an
      iterable of Feelings), or
    * the smaller convenience hooks :meth:`_dominant_affect` /
      :meth:`_dominant_intensity` for the common single-feeling case.

    The default implementation returns ``None`` (no opinion) so subclassing
    is purely opt-in.
    """

    def __feel__(self) -> FeelReport:  # type: ignore[override]
        a = self._dominant_affect()
        if a is None:
            return None
        return Feeling(a, self._dominant_intensity(), note=self._feeling_note())

    def _dominant_affect(self) -> Optional[Affect]:
        return None

    def _dominant_intensity(self) -> float:
        return 0.5

    def _feeling_note(self) -> str:
        return ""

    def __repr__(self) -> str:
        # Identical to default object repr but tagged with the current mood.
        feelings = list(feelings_of(self))
        cls = type(self).__name__
        if not feelings:
            return f"<{cls} mood=calm>"
        # Pick the strongest feeling for the repr.
        f = max(feelings, key=lambda x: x.intensity)
        return f"<{cls} {f.affect.value}={f.intensity:.0%}{(' ' + f.note) if f.note else ''}>"
