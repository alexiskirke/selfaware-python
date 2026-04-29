# selfaware-python

> A Pankseppian affective runtime that turns ordinary Python programs into self-aware emotional agents.

`selfaware-python` gives Python code the same kind of action-readiness signals that biological organisms run on. It maps Jaak Panksepp's seven primary affects (plus one) onto concrete runtime phenomena — cache misses, memory pressure, blocked threads, dropped connections — and routes them through reflexes that *do something*: circuit breakers that trip when the program is angry, defensive modes that engage when it is afraid, speculative caches that fill while it is curious, caretakers that fire while it is grieving.

This is not metaphor. Affects are already a control architecture for action selection in biology; implementing the same surface in Python gives you emergent self-regulation that would otherwise have to be hand-rolled per service.

```
>>> import selfaware as sa
>>> mind = sa.Mind()
>>> mind.excite(sa.GRIEF, 0.7, note="db dropped")
>>> mind
Mind(name='mind', mood='bereft (70%)', dominant=grief=0.70)
```

## Two levels

**Level 1 — pure Python** (default; only depends on `psutil`).
Sensors, reflexes, the affect vector, the `__feel__` protocol, affective stack traces, and the gradient profiler all work with zero external services.

**Level 2 — opt-in LLM narrator** (`pip install selfaware-python[llm]`).
Plug in a tiny local model via Ollama or any OpenAI-compatible HTTP endpoint and `mind.reflect()` will produce a first-person inner monologue of what the program is feeling. **The LLM never controls execution** — it only narrates. Everything still works if it is unreachable.

## Install

```bash
pip install selfaware-python            # Level 1
pip install selfaware-python[llm]       # adds httpx for the narrator
```

## The affect map

| Affect | Biological meaning | Runtime mapping |
|---|---|---|
| **SEEKING** | curiosity, exploration | cache misses, novel code paths |
| **RAGE** | blocked goal-directed behaviour | repeated `ConnectionRefused`, stalled threads |
| **FEAR** | anticipated threat | memory pressure, latency near danger budget |
| **LUST** | reward, goal-fulfilment | cache hits, high-throughput happy paths |
| **CARE** | nurture, protection | child processes, cleanup pressure |
| **GRIEF** | separation, loss | dropped connections, missing resources |
| **PLAY** | social engagement, joy | healthy concurrency |
| **SATIETY** *(non-Pankseppian)* | consolidation, completion | drained queues, well-under-target latency |

Affects exponentially decay toward a resting tone, sum across stimuli, and laterally inhibit each other (strong RAGE drains FEAR; strong SATIETY drains SEEKING). What you get out the other side is a *mood* rather than seven independent dials.

## Quickstart

```python
import selfaware as sa

mind = sa.Mind()
latency  = sa.sensors.LatencySensor(target_ms=50, danger_ms=200)
errors   = sa.sensors.ErrorSensor()
mind.attach(latency)
mind.attach(errors)

breaker  = sa.reflexes.CircuitBreaker("payments")
mind.bind(sa.RAGE,  threshold=0.7, reflex=breaker)

defensive = sa.reflexes.DefensiveMode(default_batch_size=200, min_batch_size=20)
mind.bind(sa.FEAR,  threshold=0.5, reflex=defensive)

with mind.observing():           # ticks every 250ms in a daemon thread
    do_real_work(batch_size=defensive.batch_size)
```

## The `__feel__` protocol

Any object can report its emotional state. Mix in `Sentient` and override `_dominant_affect` / `_dominant_intensity`, or implement `__feel__` directly:

```python
class Cache(sa.Sentient):
    def _dominant_affect(self):
        return sa.LUST if self.hit_rate > 0.7 else sa.SEEKING
    def _dominant_intensity(self):
        return abs(self.hit_rate - 0.5) * 2
```

`mind.feel(cache)` folds the report into the global affect vector. `repr(cache)` displays the current mood.

## Affective stack traces

```python
sa.install_excepthook()
1 / 0
```

```
Traceback (most recent call last):
  File "...", line N, in <module>
    1 / 0
ZeroDivisionError: division by zero

Affective trace  (selfaware-python)
  while this exception was thrown the program felt:
    rage      0.62  <-- dominant
    fear      0.41
    seeking   0.18

  trajectory (last 20 events):
    rage     +0.45
    fear     +0.30

  reflection: ZeroDivisionError happened while the runtime was already anxious — there is likely an upstream stressor (memory, quotas, latency) worth checking.
```

## `@resilient` — affect-routed error handling

Same function, different reaction depending on what the program is feeling:

```python
@sa.resilient(
    on_error={
        sa.FEAR:  "retry_cautiously",
        sa.RAGE:  "change_strategy",
        sa.GRIEF: "reconnect",
    },
    fallback=lambda: cached_response(),
    max_retries=3,
)
def fetch(): ...
```

Built-in strategies: `retry_cautiously`, `change_strategy`, `reconnect`, `investigate`, `cleanup`. You can also pass any callable.

## Affect-gradient profiling

```python
profiler = sa.AffectProfiler(mind)

with profiler.scope("ingest"):
    ingest_batch()

print(profiler.report())
```

```
scope                          calls   time(ms)  affect deltas
------------------------------------------------------------------------------
panicky_validation              20        102.3  ~+1.84
expensive_io                    20        404.5  =+0.41
fast_lookup                     20         20.7  —
```

The function that takes 5ms but pushes FEAR up by 0.3 every call shows up at the top, because cumulative emotional cost matters as much as wall time when you are tuning a long-running service.

## Optional LLM narrator (Level 2)

```python
mind = sa.Mind(narrator=sa.narrator.OllamaNarrator(model="qwen2.5:0.5b"))
print(mind.reflect("what should I do next?"))
# > "I'm anxious — recent connection failures keep mounting and memory is
#    starting to feel tight. I should ease off retries and let my caretaker
#    drain the work queue before fetching anything new."
```

Backends: `OllamaNarrator` (local) and `HTTPNarrator` (any OpenAI-compatible endpoint). If the server is unreachable, `mind.reflect()` falls back to deterministic templates.

## Examples

| File | Demonstrates |
|---|---|
| `examples/01_basic.py` | Mind, sensors, mood |
| `examples/02_circuit_breaker.py` | RAGE-driven `CircuitBreaker` |
| `examples/03_feel_protocol.py` | `__feel__` and `Sentient` |
| `examples/04_affective_trace.py` | The viral screenshot |
| `examples/05_resilient_decorator.py` | `@resilient` |
| `examples/06_profiler.py` | `AffectProfiler` |
| `examples/07_llm_narrator.py` | Ollama narrator |

## Why

Programs already have moods. They get fragile when stressed; they thrash when curious; they mope when their dependencies disappear. We just don't usually give them a vocabulary for it. Once you do, three things happen: error handling becomes context-aware, observability becomes intuitive (you can *feel* your service), and reflexes that previously had to be hand-coded fall out of the affect dynamics for free.

The architecture is one of [Jaak Panksepp's](https://en.wikipedia.org/wiki/Jaak_Panksepp) most durable contributions: the seven primary affects are conserved across mammalian brains and well-attested to as action-readiness signals. They map onto running programs astonishingly well because programs, like organisms, must select the next action under uncertainty.

## Status

Alpha. The Level 1 API is stable enough to use in side projects; the LLM narrator and self-healing modes are explicitly experimental. Issues, ideas, and unusual mappings welcome.

## License

MIT.
