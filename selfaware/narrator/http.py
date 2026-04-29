"""Generic OpenAI-compatible HTTP narrator.

Anything that speaks ``POST /v1/chat/completions`` and returns the standard
``{"choices": [{"message": {"content": ...}}]}`` shape will work here.
That covers OpenAI, vLLM, llama.cpp's server, LM Studio, Together, Groq,
and most local-LLM gateways.
"""

from __future__ import annotations

from typing import Any, Optional

from .base import Narrator


class HTTPNarrator(Narrator):
    """Talk to any OpenAI-compatible chat-completions endpoint."""

    def __init__(
        self,
        *,
        url: str,
        model: str = "default",
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        timeout: float = 10.0,
        headers: Optional[dict] = None,
    ) -> None:
        self.url = url
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self.timeout = timeout
        self.extra_headers = headers or {}

    def _complete(self, system: str, user: str) -> str:
        try:
            import httpx  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "HTTPNarrator requires `httpx`. Install with `pip install selfaware-python[llm]`."
            ) from exc

        headers = {"Content-Type": "application/json", **self.extra_headers}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature,
            "stream": False,
        }
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(self.url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        return _extract_oai(data)


def _extract_oai(data: Any) -> str:
    if isinstance(data, dict):
        choices = data.get("choices") or []
        if choices and isinstance(choices, list):
            msg = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
            if isinstance(msg, dict) and "content" in msg:
                return str(msg["content"])
    return ""
