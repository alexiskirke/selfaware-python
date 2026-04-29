"""
Example 1 — basic Mind with sensors.

Shows the smallest useful program:
  - create a Mind
  - attach a latency sensor and an error sensor
  - feed it some events
  - print the current mood
"""

import time

import selfaware as sa


def main() -> None:
    mind = sa.Mind(name="example")
    latency = sa.sensors.LatencySensor(target_ms=20, danger_ms=80)
    errors = sa.sensors.ErrorSensor()
    mind.attach(latency)
    mind.attach(errors)

    for ms in [10, 12, 9, 50, 80, 200, 220]:
        latency.record(ms)

    for _ in range(3):
        errors.record(ConnectionRefusedError("payments unreachable"))

    mind.tick()
    print("State:", mind)
    print("Mood :", mind.mood())
    print("Vector:", mind.affects)
    print()

    print("Reflection:")
    print("  ", mind.reflect())

    time.sleep(1.0)
    mind.tick()
    print()
    print("After 1s of decay:", mind.affects)


if __name__ == "__main__":
    main()
