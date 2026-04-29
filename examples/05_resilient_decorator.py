"""
Example 5 — the @resilient decorator.

The same function is retried, fallback'd, or re-raised depending on which
affect is dominant when the error happens. Built-in strategies cover the
common cases; you can pass your own callables for custom behaviour.
"""

import random

import selfaware as sa


_attempts = {"flaky": 0}


@sa.resilient(
    on_error={sa.FEAR: "retry_cautiously", sa.RAGE: "change_strategy"},
    fallback=lambda: "fallback-result",
    max_retries=4,
    backoff=0.0,
)
def flaky():
    _attempts["flaky"] += 1
    if _attempts["flaky"] < 3:
        raise TimeoutError("upstream slow")
    return "success"


def main() -> None:
    print("First call (program is calm — TimeoutError -> RAGE -> change_strategy/fallback):")
    print("  ", flaky())
    print("  attempts:", _attempts["flaky"])
    print()

    # Pre-stress with FEAR signals so the program is afraid, not angry, and
    # the decorator routes through retry_cautiously instead.
    mind = sa.default_mind()
    mind.excite(sa.FEAR, 0.6, note="seeded for demo")
    _attempts["flaky"] = 0

    print("Second call (program is fearful — TimeoutError -> retry_cautiously):")
    print("  ", flaky())
    print("  attempts:", _attempts["flaky"])


if __name__ == "__main__":
    main()
