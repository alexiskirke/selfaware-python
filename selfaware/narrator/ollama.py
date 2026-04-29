"""Ollama narrator.

Tested with Ollama 0.1.x against tiny local models — the package's
recommended default is the smallest emotionally-coherent model you can run
(e.g. ``qwen2.5:0.5b``). The narrator is intentionally cheap to call so it
can be used inline in :func:`Mind.reflect` without budget anxiety.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from .base import Narrator


class OllamaNarrator(Narrator):
    """Narrator backed by a local Ollama server."""

    def __init__(
        self,
        *,
        model: str = "qwen2.5:0.5b",
        host: str = "http://localhost:11434",
        temperature: float = 0.7,
        timeout: float = 10.0,
    ) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self.temperature = temperature
        self.timeout = timeout

    def _complete(self, system: str, user: str) -> str:
        client = _client()
        if client is None:
            raise RuntimeError(
                "OllamaNarrator requires `httpx`. Install with `pip install selfaware-python[llm]`."
            )
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": self.temperature},
        }
        url = f"{self.host}/api/chat"
        r = client.post(url, json=payload, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        return _extract(data)


def _client() -> Optional[Any]:
    try:
        import httpx  # type: ignore
    except ImportError:
        return None
    return httpx.Client()


def _extract(data: Any) -> str:
    # Ollama /api/chat returns {"message": {"role": "assistant", "content": "..."}}
    if isinstance(data, dict):
        msg = data.get("message") or {}
        if isinstance(msg, dict) and "content" in msg:
            return str(msg["content"])
        if "response" in data:
            return str(data["response"])
    return json.dumps(data)
