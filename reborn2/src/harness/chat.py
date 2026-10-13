"""Chat-completion provider (OpenAI-compatible). Stdlib only.

POST {base_url}/chat/completions with {model, messages} -> text reply.
Model-agnostic: any model ID works, and base_url can point at any
OpenAI-compatible endpoint (default: OpenRouter). Text only — decision
models can't generate prose, so drafting lives here, not in decide.py.
"""
from __future__ import annotations
import json
import os
import urllib.request
import urllib.error

DEFAULT_MODEL = "nvidia/nemotron-3.5-lightning:free"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


class ChatProvider:
    """Thin urllib client for chat completions. No extra deps."""

    name = "chat"

    def __init__(self, model: str = DEFAULT_MODEL, api_key: str | None = None,
                 base_url: str = DEFAULT_BASE_URL, timeout: int = 60):
        self.model = model
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def build_payload(self, prompt: str) -> dict:
        return {"model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "reasoning": {"enabled": False}
                }

    def complete(self, prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY missing (env or api_key=)")
        data = json.dumps(self.build_payload(prompt)).encode()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions", data=data,
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json"},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"chat {e.code}: {e.read().decode('utf-8', 'replace')[:2000]}") from e
        if isinstance(raw, dict) and "error" in raw:
            error = raw["error"]
            if isinstance(error, dict):
                message = error.get("message")
                message = message if isinstance(message, str) else str(error)[:500]
                code = error.get("code")
                metadata = error.get("metadata")
                error_type = metadata.get("error_type") if isinstance(metadata, dict) else None
                details = [str(part) for part in (code, error_type) if part is not None]
                suffix = f" ({', '.join(details)})" if details else ""
                raise RuntimeError(f"chat provider error{suffix}: {message}")
            raise RuntimeError(f"chat provider error: {str(error)[:500]}")
        try:
            content = raw["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"unexpected chat response: {str(raw)[:500]}") from e
        if isinstance(content, list):  # multipart content -> join text parts
            content = "\n".join(p.get("text", "") for p in content if p.get("type") == "text")
        return content if isinstance(content, str) else json.dumps(content)
