"""
Example 7 — Level 2: LLM narrator (Ollama).

The narrator is *opt-in*. Without it, mind.reflect() falls back to a
deterministic template. With it, you get a tiny LLM speaking in the
program's first-person voice.

Run an Ollama server first (https://ollama.com) and pull a small model:

    ollama pull qwen2.5:0.5b

Then::

    python examples/07_llm_narrator.py
"""

import argparse
import sys

import selfaware as sa


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen2.5:0.5b",
                        help="any Ollama model you've pulled locally")
    parser.add_argument("--host", default="http://localhost:11434")
    args = parser.parse_args()

    narrator = sa.narrator.OllamaNarrator(model=args.model, host=args.host)
    mind = sa.Mind(narrator=narrator, name="ollama-demo")
    errors = sa.sensors.ErrorSensor()
    mind.attach(errors)

    for _ in range(5):
        errors.record(ConnectionRefusedError("payments"))
    mind.excite(sa.SEEKING, 0.4, note="exploring failure modes")
    mind.tick()

    print("Affect vector:", mind.affects)
    print()
    print("Inner monologue:")
    try:
        print("  " + mind.reflect("what should I do next?"))
    except Exception as exc:
        print(f"  [LLM unavailable: {exc!r}]", file=sys.stderr)
        print("  " + mind._fallback_reflection())


if __name__ == "__main__":
    main()
