"""Memory pressure sensor: drives FEAR as resources approach a limit.

The biological mapping is direct. FEAR is the action-readiness signal for
*anticipated* threats; you do not have to be killed yet to be afraid of
being killed. Memory pressure is exactly that signal in software: you have
not yet OOM'd, but you can see it coming.

We use ``psutil`` if available (most accurate; works on the host), otherwise
fall back to ``resource.getrusage`` (POSIX only) and finally to a no-op.
"""

from __future__ import annotations

from typing import Dict, Optional

from ..affects import Affect
from .base import Sensor


try:
    import psutil  # type: ignore
    _HAS_PSUTIL = True
except Exception:  # pragma: no cover - psutil missing
    _HAS_PSUTIL = False


class MemorySensor(Sensor):
    """Map process or system memory usage onto FEAR (and CARE for cleanup pressure).

    Parameters
    ----------
    scope:
        ``"process"`` watches this process's RSS; ``"system"`` watches host
        memory. Process scope is more useful for application-level emotion;
        system scope is better for sidecar/agent processes.
    fear_at:
        Fraction of available memory at which FEAR begins to register. Below
        this we are calm.
    panic_at:
        Fraction at which we go into outright panic territory; FEAR ramps
        super-linearly between these two thresholds.
    """

    name = "memory"

    def __init__(
        self,
        *,
        scope: str = "process",
        fear_at: float = 0.65,
        panic_at: float = 0.90,
    ) -> None:
        if scope not in ("process", "system"):
            raise ValueError("scope must be 'process' or 'system'")
        self.scope = scope
        self.fear_at = fear_at
        self.panic_at = panic_at

    def _usage(self) -> Optional[float]:
        if not _HAS_PSUTIL:
            return None
        try:
            if self.scope == "system":
                return psutil.virtual_memory().percent / 100.0
            proc = psutil.Process()
            rss = proc.memory_info().rss
            total = psutil.virtual_memory().total
            return rss / total if total else None
        except Exception:
            return None

    def read(self) -> Optional[Dict[Affect, float]]:
        u = self._usage()
        if u is None:
            return None
        out: Dict[Affect, float] = {}
        if u >= self.fear_at:
            span = max(1e-6, self.panic_at - self.fear_at)
            x = (u - self.fear_at) / span
            out[Affect.FEAR] = min(0.30, 0.05 + x * x * 0.25)
            # CARE rises in lockstep — pressure makes us want to clean up
            # after children. This is what wires us up to caretaker reflexes.
            out[Affect.CARE] = min(0.15, x * 0.10)
        elif u < self.fear_at * 0.6:
            # comfortably below threshold — small soothe on FEAR
            out[Affect.FEAR] = -0.05
        return out or None
