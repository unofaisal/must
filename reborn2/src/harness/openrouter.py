"""OpenRouter provider. Stdlib only (urllib). No extra deps.

Docs:
- Quickstart POST https://openrouter.ai/api/v1/chat/completions
  headers: Authorization: Bearer <KEY>, Content-Type: application/json
  optional: HTTP-Referer, X-Title  (rankings/attribution)
- PDF/file input: content part {"type":"file","file":{"filename":..,"file_data": URL|data:...}}
  optional plugins: [{"id":"file-parser","pdf":{"engine":"mistral-ocr"|"native"|"cloudflare-ai"}}]
- Image input: {"type":"image_url","image_url":{"url": URL|data:...}}
- Both styles (URL + base64) handled by files.build_content.

Env: OPENROUTER_API_KEY (or pass api_key=). Model e.g. "anthropic/claude-sonnet-4".
"""
from __future__ import annotations
import json
import os
import urllib.request
import urllib.error

from .files import build_content

BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

class OpenRouterProvider:
    name = "openrouter"

    def __init__(self, model: str = "openai/gpt-4o-mini", api_key: str | None = None,
                 timeout: int = 60, pdf_engine: str | None = None,
                 site_url: str | None = None, site_title: str | None = None):
        self.model = model
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.timeout = timeout
        self.pdf_engine = pdf_engine
        self.site_url = site_url
        self.site_title = site_title
        self.last_raw: dict = {}
        self.last_annotations: list = []

    def build_payload(self, prompt: str, files: list[str] | None = None) -> dict:
        payload: dict = {
            "model": self.model,
            "messages": [{"role": "user", "content": build_content(prompt, files)}],
        }
        if self.pdf_engine:
            payload["plugins"] = [{"id": "file-parser", "pdf": {"engine": self.pdf_engine}}]
        return payload

    def _headers(self) -> dict:
        h = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        if self.site_url:
            h["HTTP-Referer"] = self.site_url
        if self.site_title:
            h["X-Title"] = self.site_title
        return h

    def complete_raw(self, prompt: str, files: list[str] | None = None) -> dict:
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY missing (env or api_key=)")
        data = json.dumps(self.build_payload(prompt, files)).encode()
        req = urllib.request.Request(BASE_URL, data=data, headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:2000]
            # error path may carry file_annotations (parsed PDF) — preserve them
            try:
                err = json.loads(body)
                anns = err.get("error", {}).get("metadata", {}).get("file_annotations", [])
                self.last_annotations = anns
            except Exception:
                pass
            raise RuntimeError(f"openrouter {e.code}: {body}") from e
        self.last_raw = raw
        try:
            self.last_annotations = raw["choices"][0]["message"].get("annotations", []) or []
        except Exception:
            self.last_annotations = []
        return raw

    def complete(self, prompt: str, files: list[str] | None = None) -> str:
        raw = self.complete_raw(prompt, files)
        try:
            msg = raw["choices"][0]["message"]
            c = msg.get("content", "")
            return c if isinstance(c, str) else json.dumps(c)
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"unexpected openrouter response: {raw}") from e
