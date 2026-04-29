"""
Example 3 — the __feel__ protocol.

Shows how user objects opt in to the affective ecosystem. A Cache reports
LUST when its hit rate is high, SEEKING when it's low, and the Mind folds
those reports into its global affect vector.
"""

import selfaware as sa


class Cache(sa.Sentient):
    def __init__(self) -> None:
        self._store = {}
        self.hits = 0
        self.misses = 0

    def get(self, key, factory):
        if key in self._store:
            self.hits += 1
            return self._store[key]
        self.misses += 1
        v = self._store[key] = factory(key)
        return v

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0

    def _dominant_affect(self):
        if self.hits + self.misses < 5:
            return None  # not enough signal
        if self.hit_rate > 0.7:
            return sa.LUST
        if self.hit_rate < 0.3:
            return sa.SEEKING
        return None

    def _dominant_intensity(self) -> float:
        if self.hit_rate > 0.5:
            return min(1.0, (self.hit_rate - 0.5) * 2.0)
        return min(1.0, (0.5 - self.hit_rate) * 2.0)

    def _feeling_note(self) -> str:
        return f"hit rate {self.hit_rate:.0%}"


def main() -> None:
    cache = Cache()

    mind = sa.Mind(name="warm-cache")
    for k in range(8):
        cache.get(k, factory=lambda kk: kk * 2)

    print("After exploration:", cache)
    mind.feel(cache)
    print("  mind:", mind.mood(), "—", mind.affects)
    print()

    cache = Cache()
    for _ in range(20):
        cache.get(0, factory=lambda kk: kk * 2)
    cache.get(99, factory=lambda kk: kk * 2)

    print("After warm-up    :", cache)
    mind = sa.Mind(name="warm-cache")
    mind.feel(cache)
    mind.tick()
    print("  mind:", mind.mood(), "—", mind.affects)


if __name__ == "__main__":
    main()
