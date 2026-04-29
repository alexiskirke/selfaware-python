"""Narrator protocol and shared prompt scaffolding."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ..affects import Affect

if TYPE_CHECKING:  # pragma: no cover
    from ..mind import Mind


SYSTEM_PROMPT = (
    "You are the inner voice of a running Python program. You speak in first "
    "person, briefly, and you stay grounded: you describe the program's "
    "current emotional state and recent trajectory, and offer one practical "
    "observation. You never invent events that are not in the state given to "
    "you. You do not output code. You write at most three short sentences."
)


def state_block(mind: "Mind") -> str:
    """Render the current affect vector + trajectory as a compact prompt block."""
    parts = []
    a, v = mind.affects.dominant()
    parts.append(f"dominant: {a.value} ({v:.2f})")
    levels = ", ".join(
        f"{aa.value}={mind.affects[aa]:.2f}"
        for aa in Affect
        if mind.affects[aa] > 0.1 and aa != a
    )
    if levels:
        parts.append(f"others: {levels}")
    traj = mind.trajectory(last=20)
    if traj:
        parts.append(
            "recent: " + ", ".join(f"{aff.value}{d:+.2f}" for aff, d in traj[:4])
        )
    return "\n".join(parts)


class Narrator:
    """Base narrator. Subclasses implement :meth:`_complete`."""

    def narrate(self, mind: "Mind", *, prompt: Optional[str] = None) -> str:
        user = state_block(mind)
        if prompt:
            user += f"\n\nuser focus: {prompt}"
        return self._complete(SYSTEM_PROMPT, user).strip()

    def _complete(self, system: str, user: str) -> str:  # pragma: no cover - interface
        raise NotImplementedError
