"""
Example 6 — affect-gradient profiler.

Measure not just how long each scope takes but how each Pankseppian affect
moves across it. The function that takes 5ms but pushes FEAR up by 0.3
every call is not actually cheap.
"""

import time

import selfaware as sa


def fast_lookup():
    time.sleep(0.001)


def expensive_io():
    time.sleep(0.02)


def panicky_validation():
    time.sleep(0.005)
    sa.default_mind().excite(sa.FEAR, 0.15, note="invariant nearly broken")


def main() -> None:
    mind = sa.default_mind()
    profiler = sa.AffectProfiler(mind)

    for _ in range(20):
        with profiler.scope("fast_lookup"):
            fast_lookup()
        with profiler.scope("expensive_io"):
            expensive_io()
        with profiler.scope("panicky_validation"):
            panicky_validation()
        mind.tick()

    print(profiler.report())


if __name__ == "__main__":
    main()
