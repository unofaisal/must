"""File helpers for OpenRouter multimodal content. Stdlib only.

Handles BOTH upload styles from the docs:
1. URL passthrough  — https://... sent as-is (efficient, no encoding)
2. Local file       — base64 data URL (required for private/local files)

Content mapping (per https://openrouter.ai/docs/guides/overview/multimodal/overview):
- images (.png/.jpg/.jpeg/.webp/.gif) -> {"type":"image_url",...}
- PDFs (.pdf)                          -> {"type":"file", "file":{...}}
- plain text (.txt/.md/.csv/.json)    -> inlined as text block
"""
from __future__ import annotations
import base64
import mimetypes
import os

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
PDF_EXTS = {".pdf"}
TEXT_EXTS = {".txt", ".md", ".csv", ".json", ".log"}
MAX_BYTES = 20 * 1024 * 1024  # 20MB guard — OpenRouter 413s on huge payloads

def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")

def _ext_of(name: str) -> str:
    base = name.split("?")[0].split("#")[0]
    _, dot, ext = base.rpartition(".")
    return ("." + ext.lower()) if dot else ""

def encode_local(path: str) -> str:
    size = os.path.getsize(path)
    if size > MAX_BYTES:
        raise ValueError(f"file too large ({size} bytes > {MAX_BYTES}): {path}")
    mime, _ = mimetypes.guess_type(path)
    mime = mime or "application/octet-stream"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"

def file_part(source: str) -> dict:
    """Build one OpenRouter content part for a URL or local path."""
    if is_url(source):
        ext = _ext_of(source)
        if ext in IMAGE_EXTS:
            return {"type": "image_url", "image_url": {"url": source}}
        # PDFs + anything else URL-based go as file type (docs: file_data accepts URL)
        return {"type": "file", "file": {"filename": source.rsplit("/", 1)[-1] or "file",
                                         "file_data": source}}
    if not os.path.isfile(source):
        raise FileNotFoundError(f"not a URL or local file: {source}")
    ext = _ext_of(source)
    name = os.path.basename(source)
    if ext in IMAGE_EXTS:
        return {"type": "image_url", "image_url": {"url": encode_local(source)}}
    if ext in PDF_EXTS:
        return {"type": "file", "file": {"filename": name, "file_data": encode_local(source)}}
    if ext in TEXT_EXTS:
        with open(source, encoding="utf-8", errors="replace") as f:
            text = f.read()
        return {"type": "text", "text": f"[file: {name}]\n{text}"}
    # unknown binary (audio/video/zip...) -> send as file data URL, let parser handle
    return {"type": "file", "file": {"filename": name, "file_data": encode_local(source)}}

def build_content(prompt: str, files: list[str] | None) -> list[dict]:
    content: list[dict] = [{"type": "text", "text": prompt}]
    for s in files or []:
        content.append(file_part(s))
    return content
