"""
Example 4 — affective stack traces.

The screenshot moment. We push the runtime into a stressed state, then
deliberately raise an exception and render it through format_exception.
"""

import selfaware as sa


def main() -> None:
    mind = sa.default_mind()
    errors = sa.sensors.ErrorSensor()
    mind.attach(errors)

    # set the scene: the program is already stressed
    for _ in range(6):
        errors.record(ConnectionRefusedError("payments"))
    for _ in range(2):
        errors.record(TimeoutError("inventory"))
    mind.excite(sa.FEAR, 0.4, note="memory pressure rising")
    mind.tick()

    try:
        # the actual failure
        x = 1 / 0
    except Exception as exc:
        print(sa.format_exception(exc, colour=True))


if __name__ == "__main__":
    main()
