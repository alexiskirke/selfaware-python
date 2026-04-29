"""
The optional LLM narrator (Level 2 of the package).

The cardinal rule: **the LLM never controls execution.** It is given a
read-only view of the affect vector and recent history, and asked to produce
plain-English commentary. The runtime continues to make all decisions
through deterministic reflexes; the narrator only talks about them.

Two backends are bundled:

* :class:`OllamaNarrator` — talks to a local `Ollama <https://ollama.com>`_
  server (default ``http://localhost:11434``).
* :class:`HTTPNarrator` — talks to any OpenAI-compatible
  ``/v1/chat/completions`` endpoint.

Both fall back gracefully: if the server is unreachable, ``narrate()``
raises and :meth:`Mind.reflect` catches the failure and returns the
deterministic fallback string. So switching the LLM on or off changes how
verbose the program becomes, never whether it works.
"""

from .base import Narrator
from .ollama import OllamaNarrator
from .http import HTTPNarrator

__all__ = ["Narrator", "OllamaNarrator", "HTTPNarrator"]
