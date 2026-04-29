"""
Example 2 — RAGE-driven circuit breaker.

Demonstrates the bundled CircuitBreaker reflex. We slam the program with
ConnectionRefused errors; RAGE rises, the breaker trips, and subsequent
calls are short-circuited until RAGE decays.
"""

import time

import selfaware as sa


def call_payments():
    raise ConnectionRefusedError("payments unreachable")


def main() -> None:
    mind = sa.Mind(name="payments")
    errors = sa.sensors.ErrorSensor()
    mind.attach(errors)

    breaker = sa.reflexes.CircuitBreaker("payments", reset_at=0.2, cooldown=2.0)
    mind.bind(sa.RAGE, threshold=0.5, reflex=breaker)

    guarded = breaker.guard(call_payments)

    for i in range(8):
        try:
            errors.record(ConnectionRefusedError())
            mind.tick()
            guarded()
        except sa.reflexes.CircuitOpen as exc:
            print(f"call {i}: SHORT-CIRCUITED ({exc}) — mood={mind.mood()}")
        except ConnectionRefusedError:
            print(f"call {i}: tried, failed     — mood={mind.mood()}")

    print()
    print("Cooling down (no new errors, RAGE decaying)...")
    for _ in range(8):
        time.sleep(0.5)
        mind.tick()
        rage = mind.affects[sa.RAGE]
        print(f"  RAGE={rage:.2f}  open={breaker.is_open}")
        if not breaker.is_open:
            break

    try:
        guarded()
    except sa.reflexes.CircuitOpen:
        print("Still open.")
    except ConnectionRefusedError:
        print(f"Recovered. Mood: {mind.mood()}")


if __name__ == "__main__":
    main()
